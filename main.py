#!/usr/bin/env python3
"""
Medical PDF Processing Pipeline - Main Entry Point (Milestone 2)

This script processes medical PDFs through the complete pipeline:
1. PDF validation and ingestion
2. OCR (Gemini 3 Preview)
3. Chunking (visit detection)
4. Structuring (Gemini 2.5 Flash → Canonical JSON)
5. Deduplication & Merge
6. Rendering (XML, PDF, DOCX)

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
from src.services.deduplication_service import DeduplicationService
# Use package-level imports to respect __init__.py configuration
from src.renderers import XMLRenderer, PDFRenderer, DOCXRenderer
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

    # Get base filename (without extension) for output naming
    input_file = Path(input_path)
    base_name = input_file.stem.replace(" ", "_").replace("(", "").replace(")", "")

    logger.info("=" * 60)
    logger.info("MEDICAL PDF PROCESSING PIPELINE - MILESTONE 2 (Complete)")
    logger.info("=" * 60)
    logger.info("Input file", path=input_path)
    logger.info("Output directory", path=output_dir)
    logger.info("Base output name", name=base_name)

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
    logger.info("STEP 2: OCR (GEMINI 3 PRO PREVIEW - AGGRESSIVE EXTRACTION)")
    logger.info("-" * 60)

    ocr_service = OCRService()
    ocr_results = ocr_service.process_pages(pdf_data["images"])

    avg_confidence = sum(r["confidence_score"] for r in ocr_results) / len(ocr_results)
    logger.info(
        "OCR complete",
        pages_processed=len(ocr_results),
        avg_confidence=round(avg_confidence, 2),
    )

    # MILESTONE 1: Save combined raw OCR output (client deliverable)
    logger.info("Saving combined raw OCR output (all pages)...")
    ocr_output_file = output_path / f"{base_name}_ocr.txt"

    with open(ocr_output_file, "w", encoding="utf-8") as f:
        for result in ocr_results:
            page_num = result["page_number"]
            # Write page separator
            f.write(f"\n{'=' * 80}\n")
            f.write(f"PAGE {page_num}\n")
            f.write(f"{'=' * 80}\n\n")
            # Write OCR text
            f.write(result["raw_text"])
            f.write("\n\n")

    logger.info(f"  • Combined OCR saved: {ocr_output_file.name}")

    # Save OCR results summary (debug)
    if get_config().debug:
        ocr_output_path = output_path / f"{base_name}_debug_ocr_results.json"
        with open(ocr_output_path, "w", encoding="utf-8") as f:
            json.dump(ocr_results, f, indent=2, ensure_ascii=False)
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
        chunks_output_path = output_path / f"{base_name}_debug_chunks.json"
        # Remove raw_text for brevity
        chunks_clean = [
            {k: v for k, v in c.items() if k != "raw_text"}
            for c in chunks
        ]
        with open(chunks_output_path, "w", encoding="utf-8") as f:
            json.dump(chunks_clean, f, indent=2, ensure_ascii=False)
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

    # Step 5: Deduplication & Merge (Milestone 2)
    logger.info("-" * 60)
    logger.info("STEP 5: DEDUPLICATION & MERGE")
    logger.info("-" * 60)

    deduplication_service = DeduplicationService(fuzzy_threshold=0.85)
    deduplicated_visits = deduplication_service.deduplicate_document(
        [visit.model_dump() if hasattr(visit, 'model_dump') else visit for visit in medical_document.visits]
    )
    medical_document.visits = deduplicated_visits

    logger.info("Deduplication complete")

    # Step 6: Save Canonical JSON
    logger.info("-" * 60)
    logger.info("STEP 6: SAVE CANONICAL JSON (SOURCE OF TRUTH)")
    logger.info("-" * 60)

    # Save canonical JSON with PDF filename
    canonical_output_path = output_path / f"{base_name}_canonical.json"
    with open(canonical_output_path, "w", encoding="utf-8") as f:
        f.write(medical_document.model_dump_json())  # Model already has indent=2
    logger.info("Canonical JSON saved", path=str(canonical_output_path))

    # Step 7: Render Outputs (Milestone 2)
    logger.info("-" * 60)
    logger.info("STEP 7: RENDER OUTPUTS (XML, PDF, DOCX)")
    logger.info("-" * 60)

    # Render XML (CCD/CCDA-style)
    logger.info("Rendering CCD/CCDA XML...")
    xml_renderer = XMLRenderer()
    xml_output_path = output_path / f"{base_name}_ccd.xml"
    xml_content = xml_renderer.render(medical_document)
    with open(xml_output_path, "w", encoding="utf-8") as f:
        f.write(xml_content)
    logger.info(f"  • CCD/CCDA XML saved: {xml_output_path.name}")

    # Render PDF (Human-readable)
    logger.info("Rendering human-readable PDF...")
    pdf_renderer = PDFRenderer()
    pdf_output_path = output_path / f"{base_name}_report.pdf"
    pdf_renderer.render(medical_document, str(pdf_output_path))
    logger.info(f"  • Human-readable PDF saved: {pdf_output_path.name}")

    # Render DOCX (Editable)
    logger.info("Rendering editable DOCX...")
    docx_renderer = DOCXRenderer()
    docx_output_path = output_path / f"{base_name}_report.docx"
    docx_renderer.render(medical_document, str(docx_output_path))
    logger.info(f"  • Editable DOCX saved: {docx_output_path.name}")

    # Summary
    logger.info("=" * 60)
    logger.info("PROCESSING COMPLETE ✓")
    logger.info("=" * 60)
    logger.info("Summary:")
    logger.info(f"  • Input: {input_path}")
    logger.info(f"  • Pages processed: {medical_document.page_count}")
    logger.info(f"  • Visits detected: {len(medical_document.visits)}")
    logger.info(f"  • OCR confidence: {medical_document.ocr_confidence_avg:.2%}")
    logger.info(f"  • Processing time: {processing_duration_ms / 1000:.1f}s")
    logger.info("")
    logger.info("Output Files:")
    logger.info(f"  • Canonical JSON: {canonical_output_path.name}")
    logger.info(f"  • Raw OCR (all pages): {ocr_output_file.name}")
    logger.info(f"  • CCD/CCDA XML: {xml_output_path.name}")
    logger.info(f"  • Human-readable PDF: {pdf_output_path.name}")
    logger.info(f"  • Editable DOCX: {docx_output_path.name}")

    if medical_document.warnings:
        logger.warning("")
        logger.warning("Warnings:", count=len(medical_document.warnings))
        for warning in medical_document.warnings:
            logger.warning(f"  • {warning}")

    return {
        "success": True,
        "base_name": base_name,
        "canonical_json": str(canonical_output_path),
        "ocr_file": str(ocr_output_file),
        "xml_file": str(xml_output_path),
        "pdf_file": str(pdf_output_path),
        "docx_file": str(docx_output_path),
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
            print("\n" + "=" * 70)
            print("✓ MILESTONE 1: PROCESSING COMPLETED SUCCESSFULLY!")
            print("=" * 70)
            print(f"\nOutput Files (Base name: {result['base_name']}):")
            print(f"  • Canonical JSON: {Path(result['canonical_json']).name}")
            print(f"  • Raw OCR Text:   {Path(result['ocr_file']).name}")
            print(f"\nQuality Metrics:")
            print(f"  • Pages processed: {result['metadata']['pages']}")
            print(f"  • OCR confidence:  {result['metadata']['confidence']:.2%}")
            print(f"  • Visits detected: {result['metadata']['visits']}")
            print(f"  • Processing time: {result['metadata']['processing_time_ms']/1000:.1f}s")
            print(f"\nOutput Directory: {Path(result['canonical_json']).parent}")
            print("\n✓ Ready for client delivery!")
            print("=" * 70)
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

# #!/usr/bin/env python3
# """
# Medical PDF Processing Pipeline - Main Entry Point

# This script processes medical PDFs through the complete pipeline:
# 1. PDF validation and ingestion
# 2. OCR (Gemini 3 Preview) with dual-pass processing
# 3. Chunking (visit detection)
# 4. Structuring (Gemini 2.5 Flash → Canonical JSON)

# Usage:
#     python main.py --input sample.pdf --output output/
# """

# import argparse
# import json
# import sys
# import time
# from pathlib import Path

# from src.services.pdf_service import PDFService, PDFValidationError
# from src.services.ocr_service import EnhancedOCRService, PageOCRResult  # ← CHANGED
# from src.services.variant_preservation import VariantPreservationSystem  # ← NEW
# from src.services.chunking_service import ChunkingService
# from src.services.structuring_service import StructuringService, StructuringError
# from src.utils.config import get_config
# from src.utils.logger import get_logger

# logger = get_logger(__name__)


# def process_medical_pdf(input_path: str, output_dir: str) -> dict:
#     """Process medical PDF through complete pipeline

#     Args:
#         input_path: Path to input PDF file
#         output_dir: Directory for output files

#     Returns:
#         Dict with processing results and output paths

#     Raises:
#         Various service-specific exceptions
#     """
#     start_time = time.time()
    
#     # Get config first
#     config = get_config()  # ← IMPORTANT: Load config

#     logger.info("=" * 60)
#     logger.info("MEDICAL PDF PROCESSING PIPELINE - MILESTONE 1 (ENHANCED)")
#     logger.info("=" * 60)
#     logger.info("Input file", path=input_path)
#     logger.info("Output directory", path=output_dir)

#     # Create output directory
#     output_path = Path(output_dir)
#     output_path.mkdir(parents=True, exist_ok=True)

#     # Step 1: PDF Validation and Ingestion
#     logger.info("-" * 60)
#     logger.info("STEP 1: PDF VALIDATION AND INGESTION")
#     logger.info("-" * 60)

#     pdf_service = PDFService()
#     pdf_data = pdf_service.process_pdf(input_path)

#     logger.info(
#         "PDF processing complete",
#         pages=pdf_data["metadata"]["page_count"],
#         file_size_mb=pdf_data["metadata"]["file_size_mb"],
#         warnings=len(pdf_data["warnings"]),
#     )

#     # Step 2: OCR (Vision-based text extraction with dual-pass)
#     logger.info("-" * 60)
#     logger.info("STEP 2: OCR (GEMINI 3 PREVIEW - DUAL-PASS PROCESSING)")
#     logger.info("-" * 60)

#     # ← FIX: Pass API key from config
#     ocr_service = EnhancedOCRService(
#         model_name=config.ocr_model_name,
#         api_key=config.gemini_api_key  # ← IMPORTANT: Pass API key
#     )
#     variant_system = VariantPreservationSystem()
    
#     ocr_results = []
#     for page_num, page_image in enumerate(pdf_data["images"], start=1):
#         logger.info(
#             "Extracting text from page",
#             page=page_num
#         )
        
#         # ← NEW: Use dual-pass extraction
#         page_result = ocr_service.extract_text_dual_pass(page_image, page_num)
        
#         # ← NEW: Validate section boundaries
#         page_result.section_boundaries = ocr_service.validate_section_boundaries(
#             page_result.full_text,
#             page_result.section_boundaries
#         )
        
#         # ← NEW: Check if manual review needed
#         needs_review, review_reasons = ocr_service.should_mark_manual_review(page_result)
#         if needs_review:
#             logger.warning(
#                 "Manual review recommended for page",
#                 page=page_num,
#                 reasons=review_reasons
#             )
        
#         logger.info(
#             "Text extraction complete",
#             page=page_num,
#             confidence=page_result.overall_confidence,
#             text_length=len(page_result.full_text),
#             blocks=len(page_result.blocks),  # ← NEW
#             needs_review=needs_review  # ← NEW
#         )
        
#         # ← NEW: Build enhanced OCR result
#         ocr_results.append({
#             "page": page_num,
#             "text": page_result.full_text,
#             "confidence_score": page_result.overall_confidence,  # Keep old key for compatibility
#             "confidence": page_result.overall_confidence,
#             # ← NEW FIELDS:
#             "blocks": [
#                 {
#                     "text": block.text[:100] + "..." if len(block.text) > 100 else block.text,
#                     "confidence": block.confidence,
#                     "block_type": block.block_type,
#                     "section": block.section,
#                     "needs_reprocessing": block.needs_reprocessing,
#                     "alternatives": block.alternatives
#                 }
#                 for block in page_result.blocks
#             ],
#             "section_boundaries": page_result.section_boundaries,
#             "needs_review": needs_review,
#             "review_reasons": review_reasons
#         })

#     # Calculate average confidence
#     if ocr_results:
#         avg_confidence = sum(r["confidence"] for r in ocr_results) / len(ocr_results)
#     else:
#         avg_confidence = 0.0
    
#     # ← NEW: Build confidence map
#     confidence_map = {}
#     for result in ocr_results:
#         page_key = f"page_{result['page']}"
#         confidence_map[page_key] = {
#             "overall": result["confidence"],
#             "blocks": result.get("blocks", [])
#         }
    
#     # ← NEW: Check if any page needs manual review
#     any_needs_review = any(r.get("needs_review", False) for r in ocr_results)
#     all_review_reasons = []
#     for r in ocr_results:
#         all_review_reasons.extend(r.get("review_reasons", []))
    
#     # ← NEW: Count statistics
#     total_blocks = sum(len(r.get("blocks", [])) for r in ocr_results)
#     low_conf_blocks = sum(
#         len([b for b in r.get("blocks", []) if b["confidence"] < 0.75])
#         for r in ocr_results
#     )
#     reprocessed_blocks = sum(
#         len([b for b in r.get("blocks", []) if b.get("needs_reprocessing") == False and b["confidence"] < 0.80])
#         for r in ocr_results
#     )
    
#     logger.info(
#         "OCR complete",
#         pages_processed=len(ocr_results),
#         avg_confidence=round(avg_confidence, 2),
#         total_blocks=total_blocks,  # ← NEW
#         low_confidence_blocks=low_conf_blocks,  # ← NEW
#         reprocessed_blocks=reprocessed_blocks,  # ← NEW
#         needs_review=any_needs_review  # ← NEW
#     )

#     # Save OCR results (debug)
#     if config.debug:
#         ocr_output_path = output_path / "debug_ocr_results.json"
#         with open(ocr_output_path, "w", encoding="utf-8") as f:
#             json.dump(ocr_results, f, indent=2)
#         logger.info("OCR debug output saved", path=str(ocr_output_path))

#     # Step 3: Chunking (Visit detection)
#     logger.info("-" * 60)
#     logger.info("STEP 3: CHUNKING (VISIT DETECTION)")
#     logger.info("-" * 60)

#     chunking_service = ChunkingService()
#     chunks = chunking_service.chunk_pages(ocr_results)

#     logger.info(
#         "Chunking complete",
#         visits_detected=len(chunks),
#         avg_pages_per_visit=sum(len(c["pages"]) for c in chunks) / len(chunks) if chunks else 0,
#     )

#     # Save chunks (debug)
#     if config.debug:
#         chunks_output_path = output_path / "debug_chunks.json"
#         # Remove raw_text for brevity
#         chunks_clean = [
#             {k: v for k, v in c.items() if k != "raw_text"}
#             for c in chunks
#         ]
#         with open(chunks_output_path, "w", encoding="utf-8") as f:
#             json.dump(chunks_clean, f, indent=2)
#         logger.info("Chunks debug output saved", path=str(chunks_output_path))

#     # Step 4: Structuring (Canonical JSON)
#     logger.info("-" * 60)
#     logger.info("STEP 4: STRUCTURING (GEMINI 2.5 FLASH → CANONICAL JSON)")
#     logger.info("-" * 60)

#     structuring_service = StructuringService()
#     medical_document = structuring_service.structure_document(chunks, ocr_results)

#     # Add processing duration
#     processing_duration_ms = int((time.time() - start_time) * 1000)
#     medical_document.processing_duration_ms = processing_duration_ms
    
#     # ← NEW: Add enhanced metadata
#     medical_document.confidence_map = confidence_map
#     medical_document.manual_review_required = any_needs_review
#     medical_document.review_reasons = list(set(all_review_reasons))  # Remove duplicates

#     logger.info(
#         "Structuring complete",
#         visits=len(medical_document.visits),
#         confidence=medical_document.ocr_confidence_avg,
#         processing_time_sec=round(processing_duration_ms / 1000, 1),
#     )

#     # Step 5: Save Canonical JSON
#     logger.info("-" * 60)
#     logger.info("STEP 5: SAVE CANONICAL JSON")
#     logger.info("-" * 60)

#     canonical_output_path = output_path / "canonical.json"
#     with open(canonical_output_path, "w", encoding="utf-8") as f:
#         f.write(medical_document.model_dump_json(indent=2))  # ← Added indent for readability
    
#     logger.info("Canonical JSON saved", path=str(canonical_output_path))
    
#     # ← NEW: Save detailed confidence report
#     confidence_report_path = output_path / "confidence_report.json"
#     with open(confidence_report_path, "w", encoding="utf-8") as f:
#         json.dump({
#             "overall_confidence": avg_confidence,
#             "confidence_map": confidence_map,
#             "manual_review_required": any_needs_review,
#             "review_reasons": list(set(all_review_reasons)),
#             "page_count": len(ocr_results),
#             "statistics": {
#                 "total_blocks": total_blocks,
#                 "low_confidence_blocks": low_conf_blocks,
#                 "reprocessed_blocks": reprocessed_blocks,
#                 "low_confidence_percentage": round((low_conf_blocks / total_blocks * 100) if total_blocks > 0 else 0, 1)
#             },
#             "processing_features": {
#                 "dual_pass_ocr": True,
#                 "section_validation": True,
#                 "variant_preservation": True,
#                 "block_level_confidence": True
#             }
#         }, f, indent=2)
    
#     logger.info("Confidence report saved", path=str(confidence_report_path))

#     # ← NEW: Save variant preservation audit (if any variants were tracked)
#     if hasattr(variant_system, 'extraction_log') and variant_system.extraction_log:
#         audit_report = variant_system.create_audit_report()
#         audit_path = output_path / "variant_audit.json"
#         with open(audit_path, "w", encoding="utf-8") as f:
#             json.dump(audit_report, f, indent=2)
#         logger.info("Variant audit saved", path=str(audit_path))

#     # Summary
#     logger.info("=" * 60)
#     logger.info("PROCESSING COMPLETE ✓")
#     logger.info("=" * 60)
#     logger.info("Summary:")
#     logger.info(f"  • Input: {input_path}")
#     logger.info(f"  • Pages processed: {medical_document.page_count}")
#     logger.info(f"  • Visits detected: {len(medical_document.visits)}")
#     logger.info(f"  • OCR confidence: {medical_document.ocr_confidence_avg:.2f}")
#     logger.info(f"  • Processing time: {processing_duration_ms / 1000:.1f}s")
#     logger.info(f"  • Output: {canonical_output_path}")
    
#     # ← NEW: Enhanced summary
#     if any_needs_review:
#         logger.warning(f"  ⚠ Manual review required: {len(set(all_review_reasons))} reasons")
#         for reason in set(all_review_reasons):
#             logger.warning(f"    • {reason}")
#     else:
#         logger.info("  ✓ No manual review required")
    
#     logger.info(f"  • Total text blocks: {total_blocks}")
#     logger.info(f"  • Low confidence blocks: {low_conf_blocks}")
#     if reprocessed_blocks > 0:
#         logger.info(f"  • Blocks reprocessed: {reprocessed_blocks}")

#     if medical_document.warnings:
#         logger.warning("Warnings:", count=len(medical_document.warnings))
#         for warning in medical_document.warnings:
#             logger.warning(f"  • {warning}")

#     return {
#         "success": True,
#         "output_file": str(canonical_output_path),
#         "confidence_report": str(confidence_report_path),  # ← NEW
#         "metadata": {
#             "pages": medical_document.page_count,
#             "visits": len(medical_document.visits),
#             "confidence": medical_document.ocr_confidence_avg,
#             "processing_time_ms": processing_duration_ms,
#             "manual_review_required": any_needs_review,  # ← NEW
#             "total_blocks": total_blocks,  # ← NEW
#             "low_confidence_blocks": low_conf_blocks  # ← NEW
#         }
#     }


# def main():
#     """Main entry point"""
#     parser = argparse.ArgumentParser(
#         description="Medical PDF Processing Pipeline - Milestone 1 (Enhanced)",
#         formatter_class=argparse.RawDescriptionHelpFormatter,
#         epilog="""
# Examples:
#   python main.py --input sample.pdf --output output/
#   python main.py -i medical_record.pdf -o results/ --debug
  
# Features:
#   • Dual-pass OCR with automatic reprocessing
#   • Block-level confidence scoring
#   • Section boundary validation
#   • Manual review flagging
#   • Variant preservation (no silent corrections)
#         """
#     )
#     parser.add_argument(
#         "-i", "--input",
#         required=True,
#         help="Path to input PDF file"
#     )
#     parser.add_argument(
#         "-o", "--output",
#         required=True,
#         help="Output directory for results"
#     )
#     parser.add_argument(
#         "--debug",
#         action="store_true",
#         help="Enable debug mode (saves intermediate outputs)"
#     )

#     args = parser.parse_args()

#     # Override debug config if flag provided
#     if args.debug:
#         import os
#         os.environ["DEBUG"] = "true"

#     try:
#         result = process_medical_pdf(args.input, args.output)

#         if result["success"]:
#             print("\n✓ Processing completed successfully!")
#             print(f"✓ Output saved to: {result['output_file']}")
#             print(f"✓ Confidence report: {result['confidence_report']}")  # ← NEW
            
#             # ← NEW: Show manual review status
#             if result['metadata'].get('manual_review_required'):
#                 print(f"\n⚠ Manual review recommended")
#                 print(f"  Low confidence blocks: {result['metadata']['low_confidence_blocks']}/{result['metadata']['total_blocks']}")
#             else:
#                 print(f"\n✓ Quality check passed - no manual review needed")
            
#             sys.exit(0)
#         else:
#             print("\n✗ Processing failed")
#             sys.exit(1)

#     except PDFValidationError as e:
#         logger.error("PDF validation failed", error=str(e))
#         print(f"\n✗ PDF Validation Error: {e}")
#         sys.exit(1)

#     except Exception as e:  # Catch OCRError and StructuringError under general Exception
#         logger.error("Processing error", error=str(e), exc_info=True)
#         print(f"\n✗ Error: {e}")
#         sys.exit(1)


# if __name__ == "__main__":
#     main()