"""PDF validation and ingestion service"""

import os
from pathlib import Path
from typing import Dict, List

from pdf2image import convert_from_path
from PIL import Image
from pypdf import PdfReader

from ..utils.config import get_config
from ..utils.logger import get_logger

logger = get_logger(__name__)


class PDFValidationError(Exception):
    """Raised when PDF validation fails"""
    pass


class PDFService:
    """Handle PDF validation, ingestion, and page extraction"""

    def __init__(self):
        self.config = get_config()

    def validate_pdf(self, pdf_path: str) -> Dict[str, any]:
        """Validate PDF file and return metadata

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dict with validation results and metadata

        Raises:
            PDFValidationError: If validation fails
        """
        logger.info("Validating PDF", pdf_path=pdf_path)

        # Check file exists
        if not os.path.exists(pdf_path):
            raise PDFValidationError(f"File not found: {pdf_path}")

        # Check file extension
        if not pdf_path.lower().endswith('.pdf'):
            raise PDFValidationError(f"Invalid file extension. Expected .pdf, got: {Path(pdf_path).suffix}")

        # Check file size
        file_size = os.path.getsize(pdf_path)
        if file_size > self.config.max_file_size_bytes:
            raise PDFValidationError(
                f"File size ({file_size / 1024 / 1024:.1f}MB) exceeds "
                f"maximum ({self.config.max_file_size_mb}MB)"
            )

        # Check if PDF is valid and not password-protected
        try:
            reader = PdfReader(pdf_path)

            # Check password protection
            if reader.is_encrypted:
                raise PDFValidationError("PDF is password-protected. Please provide unlocked version.")

            # Get page count
            page_count = len(reader.pages)

            if page_count == 0:
                raise PDFValidationError("PDF has no pages")

            if page_count > self.config.max_page_count:
                raise PDFValidationError(
                    f"Page count ({page_count}) exceeds maximum ({self.config.max_page_count})"
                )

            # Extract metadata
            metadata = {
                "page_count": page_count,
                "file_size_bytes": file_size,
                "file_size_mb": round(file_size / 1024 / 1024, 2),
                "pdf_version": reader.pdf_header if hasattr(reader, 'pdf_header') else None,
                "has_metadata": reader.metadata is not None,
            }

            logger.info(
                "PDF validation successful",
                pdf_path=pdf_path,
                page_count=page_count,
                file_size_mb=metadata["file_size_mb"],
            )

            return metadata

        except PDFValidationError:
            raise
        except Exception as e:
            logger.error("PDF validation failed", pdf_path=pdf_path, error=str(e))
            raise PDFValidationError(f"PDF file appears corrupted or invalid: {str(e)}")

    def extract_pages_as_images(self, pdf_path: str, dpi: int = 300) -> List[Image.Image]:
        """Extract PDF pages as images for OCR

        Args:
            pdf_path: Path to PDF file
            dpi: DPI for image extraction (default 300 for good quality)

        Returns:
            List of PIL Image objects, one per page

        Raises:
            PDFValidationError: If extraction fails
        """
        logger.info("Extracting pages as images", pdf_path=pdf_path, dpi=dpi)

        try:
            images = convert_from_path(pdf_path, dpi=dpi)

            if not images:
                raise PDFValidationError("No images extracted from PDF")

            logger.info(
                "Pages extracted successfully",
                pdf_path=pdf_path,
                page_count=len(images),
                dpi=dpi,
            )

            return images

        except Exception as e:
            logger.error("Page extraction failed", pdf_path=pdf_path, error=str(e))
            raise PDFValidationError(f"Failed to extract pages: {str(e)}")

    def get_page_quality_info(self, image: Image.Image, page_number: int) -> Dict[str, any]:
        """Analyze image quality for OCR suitability

        Args:
            image: PIL Image object
            page_number: Page number for logging

        Returns:
            Dict with quality metrics
        """
        width, height = image.size
        dpi_x, dpi_y = image.info.get('dpi', (None, None))

        quality_info = {
            "page_number": page_number,
            "width": width,
            "height": height,
            "dpi_x": dpi_x,
            "dpi_y": dpi_y,
            "mode": image.mode,  # RGB, L (grayscale), etc.
        }

        # Warn if DPI is low
        if dpi_x and dpi_x < 200:
            logger.warning(
                "Low resolution detected",
                page=page_number,
                dpi=dpi_x,
                recommendation="OCR confidence may be reduced"
            )
            quality_info["warning"] = f"Low resolution ({dpi_x} DPI). Recommended: 200+ DPI"

        return quality_info

    def process_pdf(self, pdf_path: str) -> Dict[str, any]:
        """Full PDF processing: validate + extract pages

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dict with metadata and extracted images

        Raises:
            PDFValidationError: If processing fails
        """
        # Step 1: Validate
        metadata = self.validate_pdf(pdf_path)

        # Step 2: Extract pages as images
        images = self.extract_pages_as_images(pdf_path)

        # Step 3: Analyze quality
        quality_info = [
            self.get_page_quality_info(img, i + 1)
            for i, img in enumerate(images)
        ]

        result = {
            "metadata": metadata,
            "images": images,
            "quality_info": quality_info,
            "warnings": [q.get("warning") for q in quality_info if q.get("warning")],
        }

        logger.info(
            "PDF processing complete",
            pdf_path=pdf_path,
            page_count=len(images),
            warnings_count=len(result["warnings"]),
        )

        return result
