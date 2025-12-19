"""Chunking service for visit/encounter detection

Groups OCR pages into logical visits/encounters using rule-based + LLM-assisted logic.
"""

import re
from datetime import datetime
from typing import Dict, List, Optional

from ..utils.logger import get_logger

logger = get_logger(__name__)


class ChunkingService:
    """Chunk OCR pages into visits/encounters"""

    def __init__(self):
        # Common medical section headers (case-insensitive patterns)
        self.visit_boundary_patterns = [
            r"(?i)^visit date:",
            r"(?i)^date of service:",
            r"(?i)^encounter date:",
            r"(?i)^admission date:",
            r"(?i)^discharge date:",
            r"(?i)^\d{1,2}/\d{1,2}/\d{2,4}",  # Date at start of line
        ]

        self.section_headers = [
            r"(?i)^chief complaint:",
            r"(?i)^reason for visit:",
            r"(?i)^history of present illness:",
            r"(?i)^hpi:",
            r"(?i)^past medical history:",
            r"(?i)^pmh:",
            r"(?i)^medications:",
            r"(?i)^allergies:",
            r"(?i)^physical exam:",
            r"(?i)^assessment:",
            r"(?i)^plan:",
            r"(?i)^impression:",
        ]

    def detect_visit_boundaries(self, ocr_pages: List[Dict[str, any]]) -> List[Dict[str, any]]:
        """Detect visit boundaries from OCR text

        Args:
            ocr_pages: List of OCR results with raw_text

        Returns:
            List of chunks (grouped pages by visit)
        """
        logger.info("Detecting visit boundaries", total_pages=len(ocr_pages))

        chunks = []
        current_chunk = {
            "visit_id": "visit_001",
            "pages": [],
            "visit_date": None,
            "raw_text": "",
        }

        visit_counter = 1

        for page in ocr_pages:
            page_number = page["page_number"]
            raw_text = page["raw_text"]

            # Check for visit boundary markers
            is_new_visit = self._is_visit_boundary(raw_text)

            if is_new_visit and current_chunk["pages"]:
                # Save current chunk and start new one
                chunks.append(current_chunk)
                visit_counter += 1
                current_chunk = {
                    "visit_id": f"visit_{visit_counter:03d}",
                    "pages": [],
                    "visit_date": None,
                    "raw_text": "",
                }

            # Add page to current chunk
            current_chunk["pages"].append(page_number)
            current_chunk["raw_text"] += f"\n--- Page {page_number} ---\n{raw_text}\n"

            # Try to extract visit date
            if not current_chunk["visit_date"]:
                visit_date = self._extract_date(raw_text)
                if visit_date:
                    current_chunk["visit_date"] = visit_date

        # Add final chunk
        if current_chunk["pages"]:
            chunks.append(current_chunk)

        logger.info(
            "Visit boundary detection complete",
            total_pages=len(ocr_pages),
            visits_detected=len(chunks),
        )

        return chunks

    def _is_visit_boundary(self, text: str) -> bool:
        """Check if text contains visit boundary markers

        Args:
            text: Raw OCR text

        Returns:
            True if this appears to start a new visit
        """
        for pattern in self.visit_boundary_patterns:
            if re.search(pattern, text, re.MULTILINE):
                return True
        return False

    def _extract_date(self, text: str) -> Optional[str]:
        """Extract date from text (ISO 8601 format)

        Args:
            text: Raw OCR text

        Returns:
            Date string in YYYY-MM-DD format or None
        """
        # Common date patterns
        date_patterns = [
            r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})",  # MM/DD/YYYY or DD-MM-YYYY
            r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})",  # YYYY-MM-DD
            r"(\d{1,2})[/-](\d{1,2})[/-](\d{2})",  # MM/DD/YY
        ]

        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    # Try to parse and normalize
                    groups = match.groups()
                    if len(groups[2]) == 4:  # YYYY format
                        if len(groups[0]) == 4:  # YYYY-MM-DD
                            year, month, day = groups
                        else:  # MM/DD/YYYY
                            month, day, year = groups
                    else:  # YY format
                        month, day, year = groups
                        year = f"20{year}" if int(year) < 50 else f"19{year}"

                    # Validate and format
                    date_obj = datetime.strptime(f"{year}-{month}-{day}", "%Y-%m-%d")
                    return date_obj.strftime("%Y-%m-%d")
                except ValueError:
                    continue

        return None

    def chunk_pages(self, ocr_results: List[Dict[str, any]]) -> List[Dict[str, any]]:
        """Main chunking method

        Args:
            ocr_results: List of OCR results from OCRService

        Returns:
            List of visit chunks with metadata
        """
        # Detect visit boundaries
        chunks = self.detect_visit_boundaries(ocr_results)

        # Add additional metadata
        for chunk in chunks:
            chunk["page_count"] = len(chunk["pages"])
            chunk["confidence"] = self._calculate_chunk_confidence(chunk, ocr_results)

        logger.info(
            "Chunking complete",
            total_visits=len(chunks),
            avg_pages_per_visit=sum(c["page_count"] for c in chunks) / len(chunks) if chunks else 0,
        )

        return chunks

    def _calculate_chunk_confidence(
        self,
        chunk: Dict[str, any],
        ocr_results: List[Dict[str, any]]
    ) -> float:
        """Calculate confidence score for a chunk

        Args:
            chunk: Visit chunk
            ocr_results: Original OCR results

        Returns:
            Confidence score (0.0-1.0)
        """
        # Get OCR confidence for pages in this chunk
        page_confidences = [
            ocr["confidence_score"]
            for ocr in ocr_results
            if ocr["page_number"] in chunk["pages"]
        ]

        if not page_confidences:
            return 0.0

        return sum(page_confidences) / len(page_confidences)
