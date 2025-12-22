"""Streamlit UI for Medical PDF Processor

Provides upload → process → download interface for medical PDF OCR processing.
Follows LLM_TECHNICAL_SPEC.md Section 12: Streamlit UI Specification
"""

import streamlit as st
import tempfile
import time
from pathlib import Path
from datetime import datetime
import traceback

from src.services.pdf_service import PDFService
from src.services.ocr_service import OCRService
from src.services.chunking_service import ChunkingService
from src.services.structuring_service import StructuringService
from src.services.deduplication_service import DeduplicationService
from src.renderers.xml_renderer import XMLRenderer
from src.renderers.pdf_renderer import PDFRenderer
from src.renderers.docx_renderer import DOCXRenderer
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Page config
st.set_page_config(
    page_title="Medical PDF Processor",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        color: #2c3e50;
        margin-bottom: 1rem;
    }
    .success-box {
        padding: 1rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 0.25rem;
        color: #155724;
    }
    .warning-box {
        padding: 1rem;
        background-color: #fff3cd;
        border: 1px solid #ffc107;
        border-radius: 0.25rem;
        color: #856404;
    }
    .error-box {
        padding: 1rem;
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 0.25rem;
        color: #721c24;
    }
</style>
""", unsafe_allow_html=True)


def initialize_services():
    """Initialize all services (cached)"""
    if 'services_initialized' not in st.session_state:
        try:
            st.session_state.pdf_service = PDFService()
            st.session_state.ocr_service = OCRService()
            st.session_state.chunking_service = ChunkingService()
            st.session_state.structuring_service = StructuringService()
            st.session_state.dedup_service = DeduplicationService()
            st.session_state.xml_renderer = XMLRenderer()
            st.session_state.pdf_renderer = PDFRenderer()
            st.session_state.docx_renderer = DOCXRenderer()
            st.session_state.services_initialized = True
            logger.info("Services initialized successfully")
        except Exception as e:
            st.error(f"Failed to initialize services: {e}")
            logger.error("Service initialization failed", error=str(e))
            st.stop()


def process_pdf(uploaded_file, progress_bar, status_text):
    """Process uploaded PDF through complete pipeline"""
    start_time = time.time()

    try:
        # Save uploaded file to temp location
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(uploaded_file.read())
            pdf_path = Path(tmp_file.name)

        logger.info("Processing PDF", filename=uploaded_file.name, size_mb=uploaded_file.size / 1024 / 1024)

        # Step 1: PDF Validation
        status_text.text("📄 Step 1/6: Validating PDF...")
        progress_bar.progress(10)

        page_count = st.session_state.pdf_service.get_page_count(str(pdf_path))
        file_size_mb = uploaded_file.size / (1024 * 1024)

        if page_count > 100:
            raise ValueError(f"PDF has {page_count} pages (max 100 allowed)")
        if file_size_mb > 50:
            raise ValueError(f"PDF is {file_size_mb:.1f}MB (max 50MB allowed)")

        # Step 2: OCR Processing
        status_text.text(f"🔍 Step 2/6: OCR Processing ({page_count} pages)...")
        progress_bar.progress(20)

        ocr_results = []
        for page_num in range(1, page_count + 1):
            status_text.text(f"🔍 Step 2/6: OCR Processing (Page {page_num}/{page_count})...")
            progress_bar.progress(20 + int((page_num / page_count) * 30))

            page_result = st.session_state.ocr_service.process_page(str(pdf_path), page_num)
            ocr_results.append(page_result)

            time.sleep(0.1)  # Brief pause for UI update

        # Step 3: Chunking
        status_text.text("📋 Step 3/6: Identifying visits...")
        progress_bar.progress(60)

        chunks = st.session_state.chunking_service.chunk_by_visit(ocr_results)
        logger.info("Chunking complete", visits=len(chunks))

        # Step 4: Structuring
        status_text.text(f"🏥 Step 4/6: Structuring medical data ({len(chunks)} visits)...")
        progress_bar.progress(70)

        document = st.session_state.structuring_service.structure_document(chunks, ocr_results)
        logger.info("Structuring complete", visits=len(document.visits))

        # Step 5: Deduplication
        status_text.text("🔄 Step 5/6: Deduplicating data...")
        progress_bar.progress(85)

        deduplicated_visits = st.session_state.dedup_service.deduplicate_document(
            [visit.model_dump() if hasattr(visit, 'model_dump') else visit for visit in document.visits]
        )
        document.visits = deduplicated_visits
        logger.info("Deduplication complete")

        # Step 6: Generate outputs
        status_text.text("📝 Step 6/6: Generating outputs...")
        progress_bar.progress(95)

        # Create output directory
        output_dir = Path(tempfile.mkdtemp())
        base_name = Path(uploaded_file.name).stem.replace(" ", "_")

        # Save canonical JSON
        json_path = output_dir / f"{base_name}_canonical.json"
        with open(json_path, "w", encoding="utf-8") as f:
            f.write(document.model_dump_json())

        # Save OCR output
        ocr_path = output_dir / f"{base_name}_ocr.txt"
        with open(ocr_path, "w", encoding="utf-8") as f:
            for result in ocr_results:
                f.write(f"\n{'=' * 80}\n")
                f.write(f"PAGE {result['page_number']}\n")
                f.write(f"{'=' * 80}\n\n")
                f.write(result["raw_text"])
                f.write("\n\n")

        # Render XML
        xml_path = output_dir / f"{base_name}_ccd.xml"
        st.session_state.xml_renderer.render(document)
        with open(xml_path, "w", encoding="utf-8") as f:
            f.write(st.session_state.xml_renderer.render(document))

        # Render PDF
        pdf_output_path = output_dir / f"{base_name}_report.pdf"
        st.session_state.pdf_renderer.render(document, str(pdf_output_path))

        # Render DOCX
        docx_path = output_dir / f"{base_name}_report.docx"
        st.session_state.docx_renderer.render(document, str(docx_path))

        progress_bar.progress(100)
        status_text.text("✅ Processing complete!")

        processing_time = time.time() - start_time

        return {
            "success": True,
            "document": document,
            "output_dir": output_dir,
            "files": {
                "json": json_path,
                "ocr": ocr_path,
                "xml": xml_path,
                "pdf": pdf_output_path,
                "docx": docx_path,
            },
            "processing_time": processing_time,
            "page_count": page_count,
        }

    except Exception as e:
        logger.error("Processing failed", error=str(e), traceback=traceback.format_exc())
        progress_bar.progress(0)
        status_text.text("")
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
        }
    finally:
        # Cleanup temp PDF
        if 'pdf_path' in locals() and pdf_path.exists():
            pdf_path.unlink()


def main():
    """Main Streamlit app"""
    initialize_services()

    # Header
    st.markdown('<div class="main-header">📄 Medical PDF Processor</div>', unsafe_allow_html=True)
    st.markdown("---")

    # Sidebar
    with st.sidebar:
        st.header("ℹ️ Information")
        st.markdown("""
        ### How to Use
        1. Upload a medical PDF (scanned or typed)
        2. Click "Process Document"
        3. Download outputs (JSON, XML, PDF, DOCX)

        ### Accepted Files
        - **Format:** PDF only
        - **Max Size:** 50 MB
        - **Max Pages:** 100
        - **Quality:** 200+ DPI recommended

        ### Privacy
        - All processing is local
        - Files are NOT stored
        - Temporary files auto-deleted
        """)

        st.markdown("---")
        st.caption("v2.0 | Milestone 2")

    # Main content
    col1, col2 = st.columns([2, 1])

    with col1:
        st.header("Step 1: Upload Document")

        uploaded_file = st.file_uploader(
            "Choose a medical PDF file",
            type=["pdf"],
            help="Upload a scanned or typed medical record PDF (max 50MB, 100 pages)"
        )

        if uploaded_file:
            # File preview
            st.success(f"✅ **{uploaded_file.name}** ({uploaded_file.size / 1024 / 1024:.2f} MB)")

            col_a, col_b = st.columns(2)
            with col_a:
                process_button = st.button("🚀 Process Document", type="primary", use_container_width=True)
            with col_b:
                cancel_button = st.button("❌ Cancel", use_container_width=True)

            if cancel_button:
                st.session_state.pop('processing_result', None)
                st.rerun()

            if process_button:
                st.markdown("---")
                st.header("Step 2: Processing")

                progress_bar = st.progress(0)
                status_text = st.empty()

                result = process_pdf(uploaded_file, progress_bar, status_text)
                st.session_state.processing_result = result

                if result["success"]:
                    st.balloons()
                else:
                    st.error(f"❌ Processing failed: {result['error']}")
                    with st.expander("Show error details"):
                        st.code(result["traceback"])

    with col2:
        st.header("📊 Quick Stats")
        if 'processing_result' in st.session_state and st.session_state.processing_result.get("success"):
            result = st.session_state.processing_result
            doc = result["document"]

            st.metric("Processing Time", f"{result['processing_time']:.1f}s")
            st.metric("Pages Processed", result["page_count"])
            st.metric("Visits Identified", len(doc.visits))
            st.metric("OCR Confidence", f"{doc.document_metadata.processing_metadata.ocr_confidence_avg * 100:.0f}%")
        else:
            st.info("Upload and process a document to see stats")

    # Results section
    if 'processing_result' in st.session_state and st.session_state.processing_result.get("success"):
        st.markdown("---")
        st.header("Step 3: Download Results")

        result = st.session_state.processing_result
        files = result["files"]
        doc = result["document"]

        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            with open(files["json"], "rb") as f:
                st.download_button(
                    "📥 Download JSON",
                    f,
                    file_name=files["json"].name,
                    mime="application/json",
                    use_container_width=True,
                )

        with col2:
            with open(files["ocr"], "rb") as f:
                st.download_button(
                    "📥 Download OCR",
                    f,
                    file_name=files["ocr"].name,
                    mime="text/plain",
                    use_container_width=True,
                )

        with col3:
            with open(files["xml"], "rb") as f:
                st.download_button(
                    "📥 Download XML",
                    f,
                    file_name=files["xml"].name,
                    mime="application/xml",
                    use_container_width=True,
                )

        with col4:
            with open(files["pdf"], "rb") as f:
                st.download_button(
                    "📥 Download PDF",
                    f,
                    file_name=files["pdf"].name,
                    mime="application/pdf",
                    use_container_width=True,
                )

        with col5:
            with open(files["docx"], "rb") as f:
                st.download_button(
                    "📥 Download DOCX",
                    f,
                    file_name=files["docx"].name,
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                )

        # Quality warnings
        if doc.data_quality.unclear_sections:
            st.markdown("---")
            st.warning("⚠️ **Quality Warnings**")
            for unclear in doc.data_quality.unclear_sections:
                st.markdown(f"- **{unclear.get('section')}** (Page {unclear.get('page')}): {unclear.get('reason')}")

        # Manual review flags
        review_needed = [v for v in doc.visits if v.get("manual_review_required")]
        if review_needed:
            st.markdown("---")
            st.warning(f"⚠️ **{len(review_needed)} visit(s) require manual review**")
            for visit in review_needed:
                reasons = ", ".join(visit.get("review_reasons", []))
                st.markdown(f"- Visit {visit.get('visit_id')}: {reasons}")


if __name__ == "__main__":
    main()
