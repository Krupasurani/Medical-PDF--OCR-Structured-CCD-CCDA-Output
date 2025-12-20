"""Structuring service using Gemini 2.5 Flash

CRITICAL: This service populates the canonical JSON schema from OCR text.
NO hallucination, NO invention, NO silent correction.
Follows LLM_SYSTEM_PROMPT.md - ROLE B: STRUCTURING ENGINE
"""

import json
from typing import Dict, List

import google.generativeai as genai

from ..models.canonical_schema import MedicalDocument
from ..utils.config import get_config
from ..utils.logger import get_logger
from ..utils.retry import retry_with_backoff

logger = get_logger(__name__)


# System prompt for Gemini 2.5 Flash (Structuring ONLY)
STRUCTURING_SYSTEM_PROMPT = """You are a medical document structuring engine. Your ONLY job is to extract structured data into JSON.

ABSOLUTE RULES:
1. Extract data ONLY from the provided OCR text
2. NO hallucination - never invent data
3. NO correction - preserve original wording exactly
4. NO medical reasoning or interpretation
5. NO expanding abbreviations (keep "HTN", "DM2" as-is)
6. If text is unclear or missing: use null or [UNCLEAR]
7. Track source page numbers for ALL data
8. Preserve all conflicts - never auto-resolve

OUTPUT SCHEMA:
Return ONLY valid JSON following this structure:
{
  "visits": [
    {
      "visit_id": "visit_001",
      "visit_date": "YYYY-MM-DD or null",
      "reason_for_visit": "exact text",
      "history_of_present_illness": "exact text",
      "medications": [
        {"name": "exact text", "dose": "exact text", "source_page": 1}
      ],
      "problem_list": [
        {"problem": "exact text", "source_page": 1}
      ],
      "results": [
        {"test_name": "exact text", "value": "exact text", "unit": "exact text", "source_page": 1}
      ],
      "assessment": "exact text",
      "plan": [
        {"action": "exact text", "source_page": 1}
      ],
      "raw_source_pages": [1, 2],
      "manual_review_required": false,
      "review_reasons": []
    }
  ]
}

CRITICAL: Return ONLY the JSON object. No explanations, no markdown formatting."""


class StructuringError(Exception):
    """Raised when structuring fails"""
    pass


class StructuringService:
    """Handle medical data structuring using Gemini 2.5 Flash"""

    def __init__(self):
        self.config = get_config()

        # Configure Gemini API
        genai.configure(api_key=self.config.gemini_api_key)

        # Model name is configurable via .env file (STRUCTURING_MODEL_NAME)
        try:
            self.model = genai.GenerativeModel(self.config.structuring_model_name)
            logger.info("Structuring service initialized", model=self.config.structuring_model_name)
        except Exception as e:
            logger.error("Failed to initialize structuring model", error=str(e))
            raise StructuringError(f"Model initialization failed: {e}")

    @retry_with_backoff(
        max_retries=3,
        initial_delay=1.0,
        retryable_exceptions=(Exception,)
    )
    def structure_visit(self, chunk: Dict[str, any]) -> Dict[str, any]:
        """Structure a single visit chunk into canonical format

        Args:
            chunk: Visit chunk with raw_text and metadata

        Returns:
            Structured visit data (dict matching Visit schema)

        Raises:
            StructuringError: If structuring fails
        """
        logger.info("Structuring visit", visit_id=chunk["visit_id"], pages=chunk["pages"])

        try:
            # Prepare prompt
            prompt = f"""{STRUCTURING_SYSTEM_PROMPT}

OCR TEXT (from pages {chunk['pages']}):
{chunk['raw_text']}

Extract structured data into JSON format. Remember:
- Preserve exact wording (no corrections)
- Use null for missing data
- Mark unclear sections with [UNCLEAR]
- Track source pages for every field
- Visit ID: {chunk['visit_id']}
- Source pages: {chunk['pages']}
"""

            # Call Gemini API with safety settings for medical content
            from google.generativeai.types import HarmCategory, HarmBlockThreshold

            safety_settings = [
                {
                    "category": HarmCategory.HARM_CATEGORY_HARASSMENT,
                    "threshold": HarmBlockThreshold.BLOCK_NONE,
                },
                {
                    "category": HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    "threshold": HarmBlockThreshold.BLOCK_NONE,
                },
                {
                    "category": HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                    "threshold": HarmBlockThreshold.BLOCK_NONE,
                },
                {
                    "category": HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                    "threshold": HarmBlockThreshold.BLOCK_NONE,
                },
            ]

            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.0,  # Deterministic
                    top_p=1.0,
                    top_k=1,
                    max_output_tokens=16384,  # Increased for longer documents
                ),
                safety_settings=safety_settings,
            )

            # Parse JSON response
            response_text = response.text.strip()

            # Remove markdown code blocks if present
            if response_text.startswith("```json"):
                response_text = response_text[7:]  # Remove ```json
            if response_text.startswith("```"):
                response_text = response_text[3:]  # Remove ```
            if response_text.endswith("```"):
                response_text = response_text[:-3]  # Remove trailing ```

            response_text = response_text.strip()

            # Parse JSON
            try:
                structured_data = json.loads(response_text)
            except json.JSONDecodeError as e:
                logger.error("Invalid JSON from model", response=response_text[:200], error=str(e))
                raise StructuringError(f"Model returned invalid JSON: {e}")

            # Extract visit data (handle both single visit and visits array)
            if "visits" in structured_data and structured_data["visits"]:
                visit_data = structured_data["visits"][0]
            else:
                visit_data = structured_data

            # Ensure required fields
            visit_data.setdefault("visit_id", chunk["visit_id"])
            visit_data.setdefault("raw_source_pages", chunk["pages"])
            visit_data.setdefault("visit_date", chunk.get("visit_date"))

            logger.info(
                "Visit structuring complete",
                visit_id=chunk["visit_id"],
                has_medications=len(visit_data.get("medications", [])) > 0,
                has_problems=len(visit_data.get("problem_list", [])) > 0,
                has_results=len(visit_data.get("results", [])) > 0,
            )

            return visit_data

        except StructuringError:
            raise
        except Exception as e:
            logger.error("Structuring failed", visit_id=chunk["visit_id"], error=str(e))
            raise StructuringError(f"Failed to structure visit {chunk['visit_id']}: {e}")

    def structure_document(
        self,
        chunks: List[Dict[str, any]],
        ocr_results: List[Dict[str, any]]
    ) -> MedicalDocument:
        """Structure entire document from chunks

        Args:
            chunks: List of visit chunks from ChunkingService
            ocr_results: Original OCR results (for metadata)

        Returns:
            Complete MedicalDocument instance

        Raises:
            StructuringError: If structuring fails
        """
        logger.info("Structuring document", total_visits=len(chunks))

        try:
            # Structure each visit
            visits_data = []
            for chunk in chunks:
                try:
                    visit_data = self.structure_visit(chunk)
                    visits_data.append(visit_data)
                except StructuringError as e:
                    logger.warning(
                        "Visit structuring failed, adding placeholder",
                        visit_id=chunk["visit_id"],
                        error=str(e),
                    )
                    # Add minimal visit with error marker
                    visits_data.append({
                        "visit_id": chunk["visit_id"],
                        "raw_source_pages": chunk["pages"],
                        "manual_review_required": True,
                        "review_reasons": [f"Structuring failed: {str(e)}"],
                    })

            # Calculate overall confidence
            avg_confidence = sum(
                ocr["confidence_score"] for ocr in ocr_results
            ) / len(ocr_results) if ocr_results else 0.0

            # Create MedicalDocument
            document = MedicalDocument(
                visits=visits_data,
                page_count=len(ocr_results),
                ocr_confidence_avg=round(avg_confidence, 2),
            )

            logger.info(
                "Document structuring complete",
                visits=len(visits_data),
                avg_confidence=round(avg_confidence, 2),
            )

            return document

        except Exception as e:
            logger.error("Document structuring failed", error=str(e))
            raise StructuringError(f"Failed to structure document: {e}")
