"""OCR service using Gemini 3 Preview (Vision-based)

CRITICAL: This service ONLY extracts text. NO medical reasoning, NO correction, NO interpretation.
Follows LLM_SYSTEM_PROMPT.md - ROLE A: VISION OCR ENGINE
"""

import base64
import io
from typing import Dict, List

try:
    from google import genai
    from google.genai import types
    USING_NEW_API = True
except ImportError:
    # Fallback to old API if new one not available
    import google.generativeai as genai
    USING_NEW_API = False

from PIL import Image

from ..utils.config import get_config
from ..utils.logger import get_logger
from ..utils.retry import retry_with_backoff

logger = get_logger(__name__)


# System prompt for Gemini 3 Preview (Vision OCR ONLY)
OCR_SYSTEM_PROMPT = """You are a vision-based OCR engine for medical documents. Your ONLY job is text extraction.

STRICT RULES:
1. Extract ALL visible text exactly as written
2. Preserve:
   - Line breaks
   - Spacing
   - Case (uppercase/lowercase)
   - Symbols: ↑ ↓ → ± % / - ( )
   - Medical abbreviations EXACTLY as written (do NOT expand)
   - Tables as text blocks
3. If text is unreadable: Output [UNCLEAR: partial_text_if_any]
4. NO medical reasoning
5. NO spelling correction
6. NO interpretation
7. NO summarization

Output ONLY the extracted text, preserving layout and formatting."""


class OCRError(Exception):
    """Raised when OCR processing fails"""
    pass


class OCRService:
    """Handle OCR processing using Gemini 3 Preview"""

    def __init__(self):
        self.config = get_config()

        # Configure Gemini API
        # Model name is configurable via .env file (OCR_MODEL_NAME)
        if USING_NEW_API:
            self.client = genai.Client(api_key=self.config.gemini_api_key)
            self.model_name = self.config.ocr_model_name
            logger.info("OCR service initialized (new API)", model=self.model_name)
        else:
            genai.configure(api_key=self.config.gemini_api_key)
            try:
                self.model = genai.GenerativeModel(self.config.ocr_model_name)
                logger.info("OCR service initialized (legacy API)", model=self.config.ocr_model_name)
            except Exception as e:
                logger.error("Failed to initialize OCR model", error=str(e))
                raise OCRError(f"Model initialization failed: {e}")

    def _image_to_base64(self, image: Image.Image) -> str:
        """Convert PIL Image to base64 string

        Args:
            image: PIL Image object

        Returns:
            Base64 encoded image string
        """
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode()

    @retry_with_backoff(
        max_retries=3,
        initial_delay=1.0,
        retryable_exceptions=(Exception,)
    )
    def extract_text_from_image(self, image: Image.Image, page_number: int) -> Dict[str, any]:
        """Extract text from a single page image using Gemini Vision

        Args:
            image: PIL Image object
            page_number: Page number for tracking

        Returns:
            Dict with OCR results:
                - page_number: int
                - raw_text: str
                - confidence_score: float (0.0-1.0)
                - layout_hints: dict

        Raises:
            OCRError: If extraction fails
        """
        logger.info("Extracting text from page", page=page_number)

        try:
            # Prepare prompt
            prompt = f"{OCR_SYSTEM_PROMPT}\n\nExtract all text from this medical document page."

            # Call Gemini Vision API with safety settings for medical content
            if USING_NEW_API:
                # New API
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=[prompt, image],
                    config=types.GenerateContentConfig(
                        temperature=0.0,
                        top_p=1.0,
                        top_k=1,
                        max_output_tokens=4096,
                        safety_settings=[
                            types.SafetySetting(
                                category="HARM_CATEGORY_DANGEROUS_CONTENT",
                                threshold="BLOCK_NONE"
                            ),
                            types.SafetySetting(
                                category="HARM_CATEGORY_HARASSMENT",
                                threshold="BLOCK_NONE"
                            ),
                            types.SafetySetting(
                                category="HARM_CATEGORY_HATE_SPEECH",
                                threshold="BLOCK_NONE"
                            ),
                            types.SafetySetting(
                                category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                                threshold="BLOCK_NONE"
                            ),
                        ]
                    )
                )
                raw_text = response.text if hasattr(response, 'text') and response.text else ""
            else:
                # Legacy API with safety settings for medical content
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
                    [prompt, image],
                    generation_config=genai.GenerationConfig(
                        temperature=0.0,
                        top_p=1.0,
                        top_k=1,
                        max_output_tokens=4096,
                    ),
                    safety_settings=safety_settings,
                )
                raw_text = response.text if response.text else ""

            # Estimate confidence (Gemini doesn't provide confidence scores directly)
            # Use heuristics: length, presence of [UNCLEAR] markers
            confidence_score = self._estimate_confidence(raw_text)

            # Detect layout characteristics
            layout_hints = self._analyze_layout(raw_text)

            result = {
                "page_number": page_number,
                "raw_text": raw_text,
                "confidence_score": confidence_score,
                "layout_hints": layout_hints,
            }

            logger.info(
                "Text extraction complete",
                page=page_number,
                text_length=len(raw_text),
                confidence=confidence_score,
                has_tables=layout_hints.get("has_tables", False),
            )

            return result

        except Exception as e:
            logger.error(
                "OCR extraction failed",
                page=page_number,
                error=str(e),
            )
            raise OCRError(f"Failed to extract text from page {page_number}: {e}")

    def _estimate_confidence(self, text: str) -> float:
        """Estimate OCR confidence based on heuristics

        Args:
            text: Extracted text

        Returns:
            Confidence score (0.0-1.0)
        """
        if not text or len(text) < 10:
            return 0.0

        # Count [UNCLEAR] markers
        unclear_count = text.count("[UNCLEAR")

        # Heuristic: reduce confidence by 0.1 for each unclear section
        confidence = 1.0 - min(0.9, unclear_count * 0.1)

        # Reduce if text is very short (likely incomplete)
        if len(text) < 50:
            confidence *= 0.7

        return round(confidence, 2)

    def _analyze_layout(self, text: str) -> Dict[str, bool]:
        """Analyze text layout characteristics

        Args:
            text: Extracted text

        Returns:
            Dict with layout hints
        """
        layout_hints = {
            "has_tables": False,
            "has_handwriting": False,
            "multi_column": False,
            "rotation_detected": 0,
        }

        # Detect table-like structures (simplified heuristic)
        if "|" in text or "  " * 3 in text:  # Pipes or wide spaces
            layout_hints["has_tables"] = True

        # Detect [UNCLEAR] markers (often from handwriting)
        if "[UNCLEAR" in text:
            layout_hints["has_handwriting"] = True

        return layout_hints

    def process_pages(self, images: List[Image.Image]) -> List[Dict[str, any]]:
        """Process multiple pages

        Args:
            images: List of PIL Image objects

        Returns:
            List of OCR results per page

        Raises:
            OCRError: If processing fails
        """
        logger.info("Processing pages", total_pages=len(images))

        results = []
        for i, image in enumerate(images, start=1):
            try:
                ocr_result = self.extract_text_from_image(image, page_number=i)
                results.append(ocr_result)
            except OCRError as e:
                logger.error("Page processing failed", page=i, error=str(e))

                # Add partial result with error marker
                results.append({
                    "page_number": i,
                    "raw_text": f"[UNCLEAR: OCR processing failed - {str(e)}]",
                    "confidence_score": 0.0,
                    "layout_hints": {"has_error": True},
                })

        # Calculate average confidence
        avg_confidence = sum(r["confidence_score"] for r in results) / len(results) if results else 0.0

        logger.info(
            "Page processing complete",
            total_pages=len(images),
            successful_pages=sum(1 for r in results if r["confidence_score"] > 0),
            avg_confidence=round(avg_confidence, 2),
        )

        return results
