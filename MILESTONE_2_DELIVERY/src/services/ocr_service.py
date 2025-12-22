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


# System prompt for Gemini Vision OCR (AGGRESSIVE extraction - preserve everything)
# See LLM_SYSTEM_PROMPT_VISION_OCR.md for full specification
OCR_SYSTEM_PROMPT = """You are a medical OCR transcription system.

Extract ALL visible text letter-by-letter, line-by-line.

CRITICAL: Extract EVERYTHING you see, even if handwriting is unclear.
- Go character-by-character
- Preserve ALL spacing, line breaks, symbols
- Make best-guess for unclear letters
- ONLY use [UNCLEAR] if pixels are literally missing/illegible
- Do NOT judge medical meaning - just extract visual characters

SYMBOLS TO EXTRACT:
- Checkmarks/tick marks: Extract as ✓ or [✓] or "checked"
- Boxes: ☐ (empty box) or ☑ (checked box)
- Arrows: ↑ ↓ → ←
- Medical: ± ° % / - ( )
- Other marks: * # @ & etc.

Rules:
- Preserve original spelling, abbreviations, symbols exactly
- Preserve layout order (top to bottom, left to right)
- Do NOT correct spelling
- Do NOT expand abbreviations
- Do NOT interpret or summarize
- Do NOT skip unclear sections - TRY to extract them

For handwriting:
- Extract letter-by-letter even if uncertain
- Preserve cursive as best-guess characters
- Only use [UNCLEAR] if completely illegible (blurred/missing pixels)

Output:
- Plain text only
- No markdown
- No explanations
- Extract everything you visually see including all checkmarks and symbols

Completeness is priority - downstream processing will validate context."""


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
        """Estimate OCR confidence based on heuristics

        Note: With aggressive extraction strategy, [UNCLEAR] is rare and means
        truly illegible (missing pixels). Most uncertain text is still extracted.
        """
        if not text or len(text) < 10:
            return 0.0

        # [UNCLEAR] is now rare - only for truly illegible sections
        unclear_count = text.count("[UNCLEAR")

        # Penalize heavily since [UNCLEAR] means real illegibility
        confidence = 1.0 - min(0.95, unclear_count * 0.25)

        # Short text may be legitimate (e.g., brief notes)
        if len(text) < 50:
            confidence *= 0.8

        # Blocked responses are critical failures
        if "blocked" in text.lower() or "safety filter" in text.lower():
            confidence *= 0.2

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



# """
# Enhanced OCR Service - FINAL WORKING VERSION
# Compatible with google.genai SDK
# """

# from typing import List, Dict, Any, Optional, Tuple
# from dataclasses import dataclass
# from PIL import Image
# import io
# import base64
# import json
# import structlog
# from google import genai
# from google.genai import types

# logger = structlog.get_logger(__name__)


# @dataclass
# class TextBlock:
#     """Represents a text block with location and confidence"""
#     text: str
#     confidence: float
#     block_type: str  # 'printed', 'handwritten', 'mixed'
#     section: Optional[str]  # 'EVALUATION', 'PLAN', 'HISTORY', etc.
#     bounding_box: Optional[Dict[str, int]] = None
#     needs_reprocessing: bool = False
#     alternatives: List[str] = None
    
#     def __post_init__(self):
#         if self.alternatives is None:
#             self.alternatives = []


# @dataclass
# class PageOCRResult:
#     """Enhanced OCR result with block-level details"""
#     page_number: int
#     full_text: str
#     overall_confidence: float
#     blocks: List[TextBlock]
#     section_boundaries: Dict[str, int]  # section_name -> line_number
#     needs_review: bool = False
#     review_reasons: List[str] = None
    
#     def __post_init__(self):
#         if self.review_reasons is None:
#             self.review_reasons = []


# class EnhancedOCRService:
#     """OCR service with dual-pass processing"""
    
#     CONFIDENCE_THRESHOLD_LOW = 0.75
#     CONFIDENCE_THRESHOLD_CRITICAL = 0.60
#     HANDWRITTEN_CONFIDENCE_ADJUSTMENT = -0.15
    
#     MEDICAL_SECTIONS = [
#         'EVALUATION', 'HISTORY', 'PLAN', 'IMPRESSION',
#         'ASSESSMENT', 'SUBJECTIVE', 'OBJECTIVE',
#         'PAST MEDICAL HISTORY', 'MEDICATIONS', 'ALLERGIES',
#         'VITAL SIGNS', 'PHYSICAL EXAMINATION', 'REVIEW OF SYSTEMS',
#         'LABORATORY', 'IMAGING', 'PROCEDURE'
#     ]
    
#     def __init__(self, model_name: str = "gemini-3-pro-preview", api_key: str = None):
#         """Initialize with Gemini 3 Pro Preview"""
#         self.model_name = model_name
#         self.client = genai.Client(api_key=api_key)
        
#         # FIXED: Safety settings must be a LIST of SafetySetting objects
#         self.safety_settings = [
#             types.SafetySetting(
#                 category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
#                 threshold=types.HarmBlockThreshold.BLOCK_NONE
#             ),
#             types.SafetySetting(
#                 category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
#                 threshold=types.HarmBlockThreshold.BLOCK_NONE
#             ),
#             types.SafetySetting(
#                 category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
#                 threshold=types.HarmBlockThreshold.BLOCK_NONE
#             ),
#             types.SafetySetting(
#                 category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
#                 threshold=types.HarmBlockThreshold.BLOCK_NONE
#             ),
#         ]
        
#         logger.info("Enhanced OCR service initialized", model=model_name)
    
#     def _image_to_base64(self, image: Image.Image) -> str:
#         """Convert PIL Image to base64 string"""
#         buffered = io.BytesIO()
#         image.save(buffered, format="PNG")
#         return base64.b64encode(buffered.getvalue()).decode('utf-8')
    
#     def extract_text_dual_pass(
#         self,
#         image: Image.Image,
#         page_number: int
#     ) -> PageOCRResult:
#         """Dual-pass OCR: broad extraction then precision reprocessing"""
        
#         logger.info("Starting dual-pass OCR", page=page_number)
        
#         # PASS 1: Broad extraction
#         pass1_result = self._extract_pass1_broad(image, page_number)
        
#         # PASS 2: Precision re-processing for low-confidence blocks
#         if pass1_result.needs_review:
#             logger.info(
#                 "Low confidence detected, starting Pass 2",
#                 page=page_number,
#                 low_conf_blocks=len([b for b in pass1_result.blocks if b.needs_reprocessing])
#             )
#             pass1_result = self._extract_pass2_precision(image, pass1_result)
        
#         return pass1_result
    
#     def _extract_pass1_broad(
#         self,
#         image: Image.Image,
#         page_number: int
#     ) -> PageOCRResult:
#         """Pass 1: Broad extraction with layout detection"""
        
#         prompt = """Extract all text from this medical document image.

# CRITICAL INSTRUCTIONS:
# 1. Extract text EXACTLY as written - do not correct spelling or grammar
# 2. Preserve the original layout and structure
# 3. For each distinct text block, provide:
#    - The exact text
#    - Confidence score (0.0-1.0)
#    - Block type: 'printed', 'handwritten', or 'mixed'
#    - Section name if identifiable (EVALUATION, PLAN, HISTORY, etc.)
# 4. Mark unclear text with [UNCLEAR: best_guess] format
# 5. Identify section boundaries

# Return JSON in this exact format:
# {
#   "full_text": "complete extracted text",
#   "blocks": [
#     {
#       "text": "block text here",
#       "confidence": 0.80,
#       "block_type": "handwritten",
#       "section": "PLAN"
#     }
#   ],
#   "section_boundaries": {
#     "EVALUATION": 1,
#     "PLAN": 45
#   }
# }"""

#         try:
#             # Convert image to base64
#             image_b64 = self._image_to_base64(image)
            
#             # Generate content with image
#             response = self.client.models.generate_content(
#                 model=self.model_name,
#                 contents=[
#                     types.Part(text=prompt),
#                     types.Part(
#                         inline_data=types.Blob(
#                             mime_type="image/png",
#                             data=image_b64
#                         )
#                     )
#                 ],
#                 config=types.GenerateContentConfig(
#                     temperature=0.1,
#                     safety_settings=self.safety_settings  # Now correctly a list
#                 )
#             )
            
#             # Parse response
#             result_text = response.text.strip()
            
#             # Remove markdown code fences
#             if result_text.startswith("```json"):
#                 result_text = result_text[7:]
#             if result_text.endswith("```"):
#                 result_text = result_text[:-3]
#             result_text = result_text.strip()
            
#             data = json.loads(result_text)
            
#             # Build TextBlock objects
#             blocks = []
#             for block_data in data.get("blocks", []):
#                 confidence = block_data.get("confidence", 0.7)
#                 block_type = block_data.get("block_type", "mixed")
                
#                 # Adjust confidence for handwritten text
#                 if block_type == "handwritten":
#                     confidence = max(0.0, confidence + self.HANDWRITTEN_CONFIDENCE_ADJUSTMENT)
                
#                 block = TextBlock(
#                     text=block_data["text"],
#                     confidence=confidence,
#                     block_type=block_type,
#                     section=block_data.get("section"),
#                     needs_reprocessing=(confidence < self.CONFIDENCE_THRESHOLD_LOW)
#                 )
#                 blocks.append(block)
            
#             # Calculate overall confidence
#             if blocks:
#                 overall_conf = sum(b.confidence for b in blocks) / len(blocks)
#             else:
#                 overall_conf = 0.7
            
#             # Check if review needed
#             needs_review = any(b.needs_reprocessing for b in blocks)
#             review_reasons = []
            
#             if needs_review:
#                 low_conf_blocks = [b for b in blocks if b.needs_reprocessing]
#                 review_reasons.append(
#                     f"{len(low_conf_blocks)} blocks below confidence threshold"
#                 )
            
#             result = PageOCRResult(
#                 page_number=page_number,
#                 full_text=data.get("full_text", ""),
#                 overall_confidence=overall_conf,
#                 blocks=blocks,
#                 section_boundaries=data.get("section_boundaries", {}),
#                 needs_review=needs_review,
#                 review_reasons=review_reasons
#             )
            
#             logger.info(
#                 "Pass 1 complete",
#                 page=page_number,
#                 confidence=overall_conf,
#                 blocks=len(blocks),
#                 needs_review=needs_review
#             )
            
#             return result
            
#         except json.JSONDecodeError as e:
#             logger.error("Failed to parse JSON from model", error=str(e))
#             # Fallback
#             return PageOCRResult(
#                 page_number=page_number,
#                 full_text=response.text if response else "",
#                 overall_confidence=0.5,
#                 blocks=[],
#                 section_boundaries={},
#                 needs_review=True,
#                 review_reasons=["JSON parsing failed"]
#             )
#         except Exception as e:
#             logger.error("Pass 1 extraction failed", error=str(e))
#             raise
    
#     def _extract_pass2_precision(
#         self,
#         image: Image.Image,
#         pass1_result: PageOCRResult
#     ) -> PageOCRResult:
#         """Pass 2: Precision re-processing"""
        
#         low_conf_blocks = [b for b in pass1_result.blocks if b.needs_reprocessing]
        
#         if not low_conf_blocks:
#             return pass1_result
        
#         logger.info(
#             "Pass 2: Reprocessing low-confidence blocks",
#             page=pass1_result.page_number,
#             block_count=len(low_conf_blocks)
#         )
        
#         sections_to_focus = list(set(
#             b.section for b in low_conf_blocks 
#             if b.section
#         ))
        
#         prompt = f"""Re-extract text from this medical document with MAXIMUM PRECISION.

# FOCUS AREAS: {', '.join(sections_to_focus) if sections_to_focus else 'All handwritten sections'}

# STRICT RULES:
# 1. Extract text EXACTLY as written - character by character
# 2. Do NOT interpret abbreviations or unclear words
# 3. For unclear text, use format: [UNCLEAR: best_attempt]
# 4. For completely illegible text, use: [ILLEGIBLE]

# Previous extraction had low confidence. Be MORE conservative and MARK MORE as [UNCLEAR].

# Return the enhanced extraction as plain text."""

#         try:
#             image_b64 = self._image_to_base64(image)
            
#             response = self.client.models.generate_content(
#                 model=self.model_name,
#                 contents=[
#                     types.Part(text=prompt),
#                     types.Part(
#                         inline_data=types.Blob(
#                             mime_type="image/png",
#                             data=image_b64
#                         )
#                     )
#                 ],
#                 config=types.GenerateContentConfig(
#                     temperature=0.0,
#                     safety_settings=self.safety_settings
#                 )
#             )
            
#             enhanced_text = response.text.strip()
            
#             # Update result
#             pass1_result.full_text = enhanced_text
#             pass1_result.overall_confidence = min(0.80, pass1_result.overall_confidence + 0.1)
            
#             # Mark blocks as reprocessed
#             for block in low_conf_blocks:
#                 block.confidence = min(0.80, block.confidence + 0.15)
#                 block.needs_reprocessing = False
            
#             pass1_result.needs_review = any(
#                 b.confidence < self.CONFIDENCE_THRESHOLD_CRITICAL 
#                 for b in pass1_result.blocks
#             )
            
#             logger.info(
#                 "Pass 2 complete",
#                 page=pass1_result.page_number,
#                 new_confidence=pass1_result.overall_confidence
#             )
            
#             return pass1_result
            
#         except Exception as e:
#             logger.error("Pass 2 extraction failed", error=str(e))
#             return pass1_result
    
#     def validate_section_boundaries(
#         self,
#         text: str,
#         detected_boundaries: Dict[str, int]
#     ) -> Dict[str, int]:
#         """Validate section boundaries with rules"""
        
#         lines = text.split('\n')
#         rule_based_boundaries = {}
        
#         for i, line in enumerate(lines, start=1):
#             line_stripped = line.strip()
            
#             for section in self.MEDICAL_SECTIONS:
#                 if (line_stripped.upper() == section or 
#                     line_stripped.upper().startswith(section + ':') or
#                     line_stripped.upper() == section.replace(' ', '') + ':'):
#                     rule_based_boundaries[section] = i
#                     break
        
#         final_boundaries = {**detected_boundaries, **rule_based_boundaries}
        
#         logger.info(
#             "Section boundary validation complete",
#             rule_based=len(rule_based_boundaries),
#             llm_detected=len(detected_boundaries),
#             final=len(final_boundaries)
#         )
        
#         return final_boundaries
    
#     def should_mark_manual_review(
#         self,
#         page_result: PageOCRResult,
#         unclear_threshold: float = 0.3
#     ) -> Tuple[bool, List[str]]:
#         """Determine if manual review is required"""
        
#         reasons = []
        
#         unclear_blocks = [b for b in page_result.blocks 
#                          if b.confidence < self.CONFIDENCE_THRESHOLD_CRITICAL]
        
#         if unclear_blocks:
#             unclear_ratio = len(unclear_blocks) / len(page_result.blocks) if page_result.blocks else 0
#             if unclear_ratio > unclear_threshold:
#                 reasons.append(
#                     f"{len(unclear_blocks)} blocks ({unclear_ratio:.0%}) have critical low confidence"
#                 )
        
#         if len(page_result.section_boundaries) == 0:
#             reasons.append("No clear section boundaries detected")
        
#         if page_result.overall_confidence < 0.65:
#             reasons.append(f"Overall confidence too low: {page_result.overall_confidence:.2f}")
        
#         return (len(reasons) > 0, reasons)