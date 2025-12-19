"""OCR service using Gemini 3 Pro Preview (Vision)

Uses: gemini-3-pro-preview - Google's latest and most intelligent vision model

CRITICAL: This service ONLY extracts text. NO medical reasoning, NO correction, NO interpretation.
"""

import base64
import io
from typing import Dict, List

# Try new API first
try:
    from google import genai
    from google.genai import types
    USING_NEW_API = True
except ImportError:
    import google.generativeai as genai
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
    USING_NEW_API = False

from PIL import Image

from ..utils.config import get_config
from ..utils.logger import get_logger
from ..utils.retry import retry_with_backoff

logger = get_logger(__name__)


# System prompt for Gemini Vision OCR
OCR_SYSTEM_PROMPT = """You are a vision-based OCR engine for medical documents. Your ONLY job is text extraction.

STRICT RULES:
1. Extract ALL visible text exactly as written
2. Preserve:
   - Line breaks and spacing
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
    """Handle OCR processing using Gemini 3 Pro Preview"""

    def __init__(self):
        self.config = get_config()
        self.model_name = self.config.ocr_model_name

        if USING_NEW_API:
            self.client = genai.Client(api_key=self.config.gemini_api_key)
            logger.info("OCR service initialized (NEW API)", model=self.model_name)
        else:
            genai.configure(api_key=self.config.gemini_api_key)
            logger.info("OCR service initialized (LEGACY API)", model=self.model_name)

    def _get_safety_settings_new_api(self):
        """Safety settings for new API - BLOCK_NONE for medical content"""
        return [
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
            types.SafetySetting(
                category="HARM_CATEGORY_DANGEROUS_CONTENT",
                threshold="BLOCK_NONE"
            ),
        ]

    def _get_safety_settings_legacy_api(self):
        """Safety settings for legacy API - BLOCK_NONE for medical content"""
        return {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }

    @retry_with_backoff(
        max_retries=3,
        initial_delay=1.0,
        retryable_exceptions=(Exception,)
    )
    def extract_text_from_image(self, image: Image.Image, page_number: int) -> Dict[str, any]:
        """Extract text from a single page image using Gemini 3 Pro Preview

        Args:
            image: PIL Image object
            page_number: Page number for tracking

        Returns:
            Dict with OCR results

        Raises:
            OCRError: If extraction fails
        """
        logger.info("Extracting text from page", page=page_number, model=self.model_name)

        try:
            prompt = f"{OCR_SYSTEM_PROMPT}\n\nExtract all text from medical document page {page_number}."

            if USING_NEW_API:
                # New API - for Gemini 3 Pro Preview
                try:
                    response = self.client.models.generate_content(
                        model=self.model_name,
                        contents=[prompt, image],
                        config=types.GenerateContentConfig(
                            temperature=0.0,
                            top_p=1.0,
                            top_k=1,
                            max_output_tokens=8192,
                            safety_settings=self._get_safety_settings_new_api(),
                            # For Gemini 3: use low thinking level for faster OCR
                            thinking_config=types.ThinkingConfig(
                                thinking_level=types.ThinkingLevel.LOW
                            ) if "3" in self.model_name else None
                        )
                    )
                    
                    # Extract text from response
                    raw_text = ""
                    if hasattr(response, 'text') and response.text:
                        raw_text = response.text
                    elif hasattr(response, 'candidates') and response.candidates:
                        candidate = response.candidates[0]
                        if hasattr(candidate, 'content') and candidate.content:
                            if hasattr(candidate.content, 'parts'):
                                raw_text = ''.join(
                                    part.text for part in candidate.content.parts 
                                    if hasattr(part, 'text')
                                )
                    
                    # Check for blocking
                    if not raw_text and hasattr(response, 'candidates') and response.candidates:
                        candidate = response.candidates[0]
                        if hasattr(candidate, 'finish_reason'):
                            finish_reason = str(candidate.finish_reason)
                            logger.warning(
                                "Response may be blocked",
                                page=page_number,
                                finish_reason=finish_reason
                            )
                            if '2' in finish_reason or 'SAFETY' in finish_reason.upper():
                                raw_text = f"[UNCLEAR: Page {page_number} - Response blocked by safety filter]"
                
                except Exception as e:
                    logger.error("New API call failed", page=page_number, error=str(e))
                    raise

            else:
                # Legacy API
                model = genai.GenerativeModel(self.model_name)
                
                try:
                    response = model.generate_content(
                        [prompt, image],
                        generation_config=genai.GenerationConfig(
                            temperature=0.0,
                            top_p=1.0,
                            top_k=1,
                            max_output_tokens=8192,
                        ),
                        safety_settings=self._get_safety_settings_legacy_api()
                    )
                    
                    # Handle blocked responses
                    raw_text = ""
                    if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                        if hasattr(response.prompt_feedback, 'block_reason'):
                            block_reason = response.prompt_feedback.block_reason
                            logger.warning(
                                "Prompt blocked",
                                page=page_number,
                                reason=str(block_reason)
                            )
                            raw_text = f"[UNCLEAR: Page {page_number} - Prompt blocked: {block_reason}]"
                    
                    # Check for content
                    if not raw_text:
                        if hasattr(response, 'parts') and response.parts:
                            raw_text = response.text
                        elif hasattr(response, 'candidates') and response.candidates:
                            candidate = response.candidates[0]
                            if hasattr(candidate, 'finish_reason'):
                                finish_reason = candidate.finish_reason
                                logger.warning(
                                    "Response incomplete",
                                    page=page_number,
                                    finish_reason=str(finish_reason)
                                )
                                
                                # Map finish reasons
                                finish_reason_val = finish_reason if isinstance(finish_reason, int) else 0
                                
                                if finish_reason_val == 2:  # SAFETY
                                    raw_text = f"[UNCLEAR: Page {page_number} - Blocked by safety filter]"
                                elif finish_reason_val == 3:  # RECITATION
                                    raw_text = f"[UNCLEAR: Page {page_number} - Blocked due to recitation]"
                                else:
                                    raw_text = f"[UNCLEAR: Page {page_number} - No content (finish_reason: {finish_reason})]"
                            else:
                                raw_text = f"[UNCLEAR: Page {page_number} - No text extracted]"
                        else:
                            raw_text = f"[UNCLEAR: Page {page_number} - Empty response]"
                
                except Exception as e:
                    logger.error("Legacy API call failed", page=page_number, error=str(e))
                    raise

            # Handle empty response
            if not raw_text or len(raw_text.strip()) < 5:
                logger.warning("Minimal extraction", page=page_number, text_len=len(raw_text))
                if not raw_text:
                    raw_text = f"[UNCLEAR: No text detected on page {page_number}]"

            # Estimate confidence
            confidence_score = self._estimate_confidence(raw_text)

            # Detect layout
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
            )

            return result

        except Exception as e:
            logger.error(
                "OCR extraction failed",
                page=page_number,
                error=str(e),
                error_type=type(e).__name__
            )
            raise OCRError(f"Failed to extract text from page {page_number}: {e}")

    def _estimate_confidence(self, text: str) -> float:
        """Estimate OCR confidence based on heuristics"""
        if not text or len(text) < 10:
            return 0.0

        unclear_count = text.count("[UNCLEAR")
        confidence = 1.0 - min(0.9, unclear_count * 0.15)

        if len(text) < 50:
            confidence *= 0.7

        if "blocked" in text.lower() or "safety filter" in text.lower():
            confidence *= 0.3

        return round(confidence, 2)

    def _analyze_layout(self, text: str) -> Dict[str, bool]:
        """Analyze text layout characteristics"""
        layout_hints = {
            "has_tables": False,
            "has_handwriting": False,
            "multi_column": False,
            "rotation_detected": 0,
        }

        if "|" in text or "  " * 3 in text:
            layout_hints["has_tables"] = True

        if "[UNCLEAR" in text:
            layout_hints["has_handwriting"] = True

        return layout_hints

    def process_pages(self, images: List[Image.Image]) -> List[Dict[str, any]]:
        """Process multiple pages"""
        logger.info("Processing pages", total_pages=len(images), model=self.model_name)

        results = []
        for i, image in enumerate(images, start=1):
            try:
                ocr_result = self.extract_text_from_image(image, page_number=i)
                results.append(ocr_result)
            except OCRError as e:
                logger.error("Page processing failed", page=i, error=str(e))
                results.append({
                    "page_number": i,
                    "raw_text": f"[UNCLEAR: OCR processing failed - {str(e)}]",
                    "confidence_score": 0.0,
                    "layout_hints": {"has_error": True},
                })

        avg_confidence = sum(r["confidence_score"] for r in results) / len(results) if results else 0.0

        logger.info(
            "Page processing complete",
            total_pages=len(images),
            successful_pages=sum(1 for r in results if r["confidence_score"] > 0),
            avg_confidence=round(avg_confidence, 2),
        )

        return results