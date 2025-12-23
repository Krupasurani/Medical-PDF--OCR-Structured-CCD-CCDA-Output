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
7. Track source page numbers AND line numbers for ALL data
8. Preserve all conflicts - never auto-resolve

JSON FORMATTING RULES (CRITICAL):
- Escape all special characters in strings
- Replace " with \\" in all text values
- Replace \\ with \\\\ in all text values
- Replace newlines with \\n
- Ensure all strings are properly closed with "
- DO NOT truncate strings - complete all text values
- If a value is very long, include it fully or use null

ENTERPRISE IMPROVEMENT #2: Source Traceability
- For EVERY extracted field, include the exact text snippet from OCR
- Include line number where the text appears
- Format: "source_excerpt": "exact text from line X"

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
        {
          "name": "exact text",
          "dose": "exact text",
          "source_page": 1,
          "source_line": 15,
          "source_excerpt": "exact 40-char snippet from OCR"
        }
      ],
      "problem_list": [
        {
          "problem": "exact text",
          "source_page": 1,
          "source_line": 20,
          "source_excerpt": "exact 40-char snippet from OCR"
        }
      ],
      "results": [
        {
          "test_name": "exact text",
          "value": "exact text",
          "unit": "exact text",
          "source_page": 1,
          "source_line": 25,
          "source_excerpt": "exact 40-char snippet from OCR"
        }
      ],
      "assessment": "exact text",
      "plan": [
        {
          "action": "exact text",
          "source_page": 1,
          "source_line": 30,
          "source_excerpt": "exact 40-char snippet from OCR"
        }
      ],
      "raw_source_pages": [1, 2],
      "manual_review_required": false,
      "review_reasons": []
    }
  ]
}

CRITICAL:
- Return ONLY valid, complete JSON
- No explanations, no markdown formatting
- Ensure ALL strings are properly closed
- Complete all text values, do not truncate"""


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
            # Prepare line-numbered OCR text for better traceability
            lines = chunk['raw_text'].split('\n')
            line_numbered_text = '\n'.join([f"{i+1:4d}| {line}" for i, line in enumerate(lines)])

            # Prepare prompt
            prompt = f"""{STRUCTURING_SYSTEM_PROMPT}

OCR TEXT WITH LINE NUMBERS (from pages {chunk['pages']}):
{line_numbered_text}

Extract structured data into JSON format. Remember:
- Preserve exact wording (no corrections)
- Use null for missing data
- Mark unclear sections with [UNCLEAR]
- Track source pages AND line numbers for every field
- Include exact text excerpts (40-60 chars) for traceability
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

            # Extract actual token usage from API response
            usage_metadata = {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0
            }
            if hasattr(response, 'usage_metadata'):
                usage_metadata["prompt_tokens"] = getattr(response.usage_metadata, 'prompt_token_count', 0)
                usage_metadata["completion_tokens"] = getattr(response.usage_metadata, 'candidates_token_count', 0)
                usage_metadata["total_tokens"] = getattr(response.usage_metadata, 'total_token_count', 0)

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

            # Fix: Convert None to empty strings for string fields (Pydantic v2 strict typing)
            string_fields = [
                "reason_for_visit",
                "history_of_present_illness",
                "assessment"
            ]
            for field in string_fields:
                if visit_data.get(field) is None:
                    visit_data[field] = ""

            # Enterprise Improvement #2: Enrich with source excerpts if missing
            visit_data = self._enrich_source_excerpts(visit_data, chunk['raw_text'])

            # Add token usage metadata
            visit_data["_usage_metadata"] = usage_metadata

            logger.info(
                "Visit structuring complete",
                visit_id=chunk["visit_id"],
                has_medications=len(visit_data.get("medications", [])) > 0,
                has_problems=len(visit_data.get("problem_list", [])) > 0,
                has_results=len(visit_data.get("results", [])) > 0,
                prompt_tokens=usage_metadata["prompt_tokens"],
                completion_tokens=usage_metadata["completion_tokens"],
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
            total_token_usage = {"input": 0, "output": 0, "calls": 0}

            for chunk in chunks:
                try:
                    visit_data = self.structure_visit(chunk)

                    # Extract token usage before Pydantic validation strips it
                    if "_usage_metadata" in visit_data:
                        total_token_usage["input"] += visit_data["_usage_metadata"]["prompt_tokens"]
                        total_token_usage["output"] += visit_data["_usage_metadata"]["completion_tokens"]
                        total_token_usage["calls"] += 1
                        # Remove it so Pydantic doesn't complain
                        del visit_data["_usage_metadata"]

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

            # Combine raw OCR text from all pages for LLM-based rendering
            raw_ocr_text = ""
            for result in ocr_results:
                page_num = result.get("page_number", result.get("page", 0))
                raw_ocr_text += f"\n{'=' * 80}\n"
                raw_ocr_text += f"PAGE {page_num}\n"
                raw_ocr_text += f"{'=' * 80}\n\n"
                raw_ocr_text += result.get("raw_text", result.get("text", ""))
                raw_ocr_text += "\n\n"

            # Create MedicalDocument
            document = MedicalDocument(
                visits=visits_data,
                page_count=len(ocr_results),
                ocr_confidence_avg=round(avg_confidence, 2),
                raw_ocr_text=raw_ocr_text.strip(),  # Store complete OCR text
            )

            # Attach token usage for developer logging (not part of schema)
            document._structuring_token_usage = total_token_usage

            logger.info(
                "Document structuring complete",
                visits=len(visits_data),
                avg_confidence=round(avg_confidence, 2),
                structuring_input_tokens=total_token_usage["input"],
                structuring_output_tokens=total_token_usage["output"],
                structuring_calls=total_token_usage["calls"],
            )

            return document

        except Exception as e:
            logger.error("Document structuring failed", error=str(e))
            raise StructuringError(f"Failed to structure document: {e}")

    def _enrich_source_excerpts(self, visit_data: Dict, ocr_text: str) -> Dict:
        """Enrich structured data with source excerpts if missing

        ENTERPRISE IMPROVEMENT #2: Ensure every data point has exact source traceability
        - Find exact text in OCR
        - Add line number
        - Add 50-char excerpt for context
        """
        lines = ocr_text.split('\n')

        def find_excerpt(text_to_find: str) -> Dict[str, any]:
            """Find text in OCR and return line number + excerpt"""
            if not text_to_find or text_to_find == "N/A" or text_to_find == "null":
                return {}

            # Search for text in lines
            for line_num, line in enumerate(lines, start=1):
                if text_to_find.lower() in line.lower():
                    # Found it! Extract 50-char context
                    start_idx = max(0, line.lower().find(text_to_find.lower()) - 10)
                    end_idx = min(len(line), start_idx + 60)
                    excerpt = line[start_idx:end_idx].strip()

                    return {
                        "source_line": line_num,
                        "source_excerpt": excerpt[:60]  # Cap at 60 chars
                    }

            # Not found - return empty
            return {}

        # Enrich medications
        for med in visit_data.get("medications", []):
            if "source_line" not in med or "source_excerpt" not in med:
                med_name = med.get("name", "")
                enrichment = find_excerpt(med_name)
                med.update(enrichment)

        # Enrich problems
        for problem in visit_data.get("problem_list", []):
            if "source_line" not in problem or "source_excerpt" not in problem:
                problem_text = problem.get("problem", "")
                enrichment = find_excerpt(problem_text)
                problem.update(enrichment)

        # Enrich results
        for result in visit_data.get("results", []):
            if "source_line" not in result or "source_excerpt" not in result:
                test_name = result.get("test_name", "")
                enrichment = find_excerpt(test_name)
                result.update(enrichment)

        # Enrich plan items
        for plan_item in visit_data.get("plan", []):
            if "source_line" not in plan_item or "source_excerpt" not in plan_item:
                action = plan_item.get("action", "")
                enrichment = find_excerpt(action)
                plan_item.update(enrichment)

        return visit_data
