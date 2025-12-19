#!/usr/bin/env python3
"""
Medical PDF Processing Pipeline - Main Entry Point

This script processes medical PDFs through the complete pipeline:
1. PDF validation and ingestion
2. OCR (Gemini 3 Preview)
3. Chunking (visit detection)
4. Structuring (Gemini 2.5 Flash → Canonical JSON)

Usage:
    python main.py --input sample.pdf --output output/
"""

import argparse
import json
import sys
import time
from pathlib import Path

from src.services.pdf_service import PDFService, PDFValidationError
from src.services.ocr_service import OCRService, OCRError
from src.services.chunking_service import ChunkingService
from src.services.structuring_service import StructuringService, StructuringError
from src.utils.config import get_config
from src.utils.logger import get_logger

logger = get_logger(__name__)


def process_medical_pdf(input_path: str, output_dir: str) -> dict:
    """Process medical PDF through complete pipeline

    Args:
        input_path: Path to input PDF file
        output_dir: Directory for output files

    Returns:
        Dict with processing results and output paths

    Raises:
        Various service-specific exceptions
    """
    start_time = time.time()

    logger.info("=" * 60)
    logger.info("MEDICAL PDF PROCESSING PIPELINE - MILESTONE 1")
    logger.info("=" * 60)
    logger.info("Input file", path=input_path)
    logger.info("Output directory", path=output_dir)

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Step 1: PDF Validation and Ingestion
    logger.info("-" * 60)
    logger.info("STEP 1: PDF VALIDATION AND INGESTION")
    logger.info("-" * 60)

    pdf_service = PDFService()
    pdf_data = pdf_service.process_pdf(input_path)

    logger.info(
        "PDF processing complete",
        pages=pdf_data["metadata"]["page_count"],
        file_size_mb=pdf_data["metadata"]["file_size_mb"],
        warnings=len(pdf_data["warnings"]),
    )

    # Step 2: OCR (Vision-based text extraction)
    logger.info("-" * 60)
    logger.info("STEP 2: OCR (GEMINI 3 PREVIEW - VISION)")
    logger.info("-" * 60)

    ocr_service = OCRService()
    ocr_results = ocr_service.process_pages(pdf_data["images"])

    avg_confidence = sum(r["confidence_score"] for r in ocr_results) / len(ocr_results)
    logger.info(
        "OCR complete",
        pages_processed=len(ocr_results),
        avg_confidence=round(avg_confidence, 2),
    )

    # Save OCR results (debug)
    if get_config().debug:
        ocr_output_path = output_path / "debug_ocr_results.json"
        with open(ocr_output_path, "w") as f:
            json.dump(ocr_results, f, indent=2)
        logger.info("OCR debug output saved", path=str(ocr_output_path))

    # Step 3: Chunking (Visit detection)
    logger.info("-" * 60)
    logger.info("STEP 3: CHUNKING (VISIT DETECTION)")
    logger.info("-" * 60)

    chunking_service = ChunkingService()
    chunks = chunking_service.chunk_pages(ocr_results)

    logger.info(
        "Chunking complete",
        visits_detected=len(chunks),
        avg_pages_per_visit=sum(len(c["pages"]) for c in chunks) / len(chunks) if chunks else 0,
    )

    # Save chunks (debug)
    if get_config().debug:
        chunks_output_path = output_path / "debug_chunks.json"
        # Remove raw_text for brevity
        chunks_clean = [
            {k: v for k, v in c.items() if k != "raw_text"}
            for c in chunks
        ]
        with open(chunks_output_path, "w") as f:
            json.dump(chunks_clean, f, indent=2)
        logger.info("Chunks debug output saved", path=str(chunks_output_path))

    # Step 4: Structuring (Canonical JSON)
    logger.info("-" * 60)
    logger.info("STEP 4: STRUCTURING (GEMINI 2.5 FLASH → CANONICAL JSON)")
    logger.info("-" * 60)

    structuring_service = StructuringService()
    medical_document = structuring_service.structure_document(chunks, ocr_results)

    # Add processing duration
    processing_duration_ms = int((time.time() - start_time) * 1000)
    medical_document.processing_duration_ms = processing_duration_ms

    logger.info(
        "Structuring complete",
        visits=len(medical_document.visits),
        confidence=medical_document.ocr_confidence_avg,
        processing_time_sec=round(processing_duration_ms / 1000, 1),
    )

    # Step 5: Save Canonical JSON
    logger.info("-" * 60)
    logger.info("STEP 5: SAVE CANONICAL JSON")
    logger.info("-" * 60)

    canonical_output_path = output_path / "canonical.json"
    with open(canonical_output_path, "w") as f:
        f.write(medical_document.model_dump_json())

    logger.info("Canonical JSON saved", path=str(canonical_output_path))

    # Summary
    logger.info("=" * 60)
    logger.info("PROCESSING COMPLETE ✓")
    logger.info("=" * 60)
    logger.info("Summary:")
    logger.info(f"  • Input: {input_path}")
    logger.info(f"  • Pages processed: {medical_document.page_count}")
    logger.info(f"  • Visits detected: {len(medical_document.visits)}")
    logger.info(f"  • OCR confidence: {medical_document.ocr_confidence_avg:.2f}")
    logger.info(f"  • Processing time: {processing_duration_ms / 1000:.1f}s")
    logger.info(f"  • Output: {canonical_output_path}")

    if medical_document.warnings:
        logger.warning("Warnings:", count=len(medical_document.warnings))
        for warning in medical_document.warnings:
            logger.warning(f"  • {warning}")

    return {
        "success": True,
        "output_file": str(canonical_output_path),
        "metadata": {
            "pages": medical_document.page_count,
            "visits": len(medical_document.visits),
            "confidence": medical_document.ocr_confidence_avg,
            "processing_time_ms": processing_duration_ms,
        }
    }


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Medical PDF Processing Pipeline - Milestone 1",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --input sample.pdf --output output/
  python main.py -i medical_record.pdf -o results/ --debug
        """
    )
    parser.add_argument(
        "-i", "--input",
        required=True,
        help="Path to input PDF file"
    )
    parser.add_argument(
        "-o", "--output",
        required=True,
        help="Output directory for results"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode (saves intermediate outputs)"
    )

    args = parser.parse_args()

    # Override debug config if flag provided
    if args.debug:
        import os
        os.environ["DEBUG"] = "true"

    try:
        result = process_medical_pdf(args.input, args.output)

        if result["success"]:
            print("\n✓ Processing completed successfully!")
            print(f"✓ Output saved to: {result['output_file']}")
            sys.exit(0)
        else:
            print("\n✗ Processing failed")
            sys.exit(1)

    except PDFValidationError as e:
        logger.error("PDF validation failed", error=str(e))
        print(f"\n✗ PDF Validation Error: {e}")
        sys.exit(1)

    except OCRError as e:
        logger.error("OCR processing failed", error=str(e))
        print(f"\n✗ OCR Error: {e}")
        sys.exit(1)

    except StructuringError as e:
        logger.error("Structuring failed", error=str(e))
        print(f"\n✗ Structuring Error: {e}")
        sys.exit(1)

    except Exception as e:
        logger.error("Unexpected error", error=str(e), exc_info=True)
        print(f"\n✗ Unexpected Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
