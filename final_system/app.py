"""
Medical PDF OCR to CCD/CCDA Converter - Web UI
Enterprise-grade medical document processing with LLM-based XML generation
"""

import streamlit as st
import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.pdf_service import PDFService
from app.services.ocr_service import OCRService
from app.services.chunking_service import ChunkingService
from app.services.structuring_service import StructuringService
from app.services.deduplication_service import DeduplicationService
from app.renderers import XMLRenderer, PDFRenderer, DOCXRenderer
from app.utils.config import get_config
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Page configuration
st.set_page_config(
    page_title="Medical PDF → CCD/CCDA Converter",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .success-box {
        background: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .warning-box {
        background: #fff3cd;
        border: 1px solid #ffeaa7;
        color: #856404;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .error-box {
        background: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)


def process_medical_pdf(uploaded_file, output_dir: str) -> dict:
    """Process medical PDF through complete pipeline"""
    start_time = time.time()

    # Save uploaded file temporarily
    temp_input_path = output_dir / "temp_input.pdf"
    with open(temp_input_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    try:
        # Get base filename for outputs
        base_name = Path(uploaded_file.name).stem.replace(" ", "_").replace("(", "").replace(")", "")

        progress_bar = st.progress(0)
        status_text = st.empty()

        # Step 1: PDF Validation (10%)
        status_text.text("📄 Step 1/7: Validating PDF...")
        progress_bar.progress(10)
        pdf_service = PDFService()
        pdf_data = pdf_service.process_pdf(str(temp_input_path))

        # Step 2: OCR (30%)
        status_text.text(f"🔍 Step 2/7: Running OCR on {pdf_data['metadata']['page_count']} pages...")
        progress_bar.progress(30)
        ocr_service = OCRService()
        ocr_results = ocr_service.process_pages(pdf_data["images"])

        # Save OCR text
        ocr_output_file = output_dir / f"{base_name}_ocr.txt"
        with open(ocr_output_file, "w", encoding="utf-8") as f:
            for result in ocr_results:
                page_num = result["page_number"]
                f.write(f"\n{'=' * 80}\n")
                f.write(f"PAGE {page_num}\n")
                f.write(f"{'=' * 80}\n\n")
                f.write(result["raw_text"])
                f.write("\n\n")

        # Step 3: Chunking (45%)
        status_text.text("📊 Step 3/7: Detecting visits...")
        progress_bar.progress(45)
        chunking_service = ChunkingService()
        chunks = chunking_service.chunk_pages(ocr_results)

        # Step 4: Structuring (60%)
        status_text.text("🧠 Step 4/7: Structuring data with AI...")
        progress_bar.progress(60)
        structuring_service = StructuringService()
        medical_document = structuring_service.structure_document(chunks, ocr_results)

        processing_duration_ms = int((time.time() - start_time) * 1000)
        medical_document.processing_duration_ms = processing_duration_ms

        # Step 5: Deduplication (70%)
        status_text.text("🔄 Step 5/7: Removing duplicates...")
        progress_bar.progress(70)
        deduplication_service = DeduplicationService(fuzzy_threshold=0.85)
        deduplicated_visits = deduplication_service.deduplicate_document(
            [visit.model_dump() if hasattr(visit, 'model_dump') else visit
             for visit in medical_document.visits]
        )
        medical_document.visits = deduplicated_visits

        # Step 6: Save Canonical JSON (80%)
        status_text.text("💾 Step 6/7: Saving canonical JSON...")
        progress_bar.progress(80)
        canonical_output_path = output_dir / f"{base_name}_canonical.json"
        with open(canonical_output_path, "w", encoding="utf-8") as f:
            f.write(medical_document.model_dump_json())

        # Step 7: Render Outputs (95%)
        status_text.text("📝 Step 7/7: Generating XML, PDF, and DOCX...")
        progress_bar.progress(95)

        # XML (CCD/CCDA with LLM)
        xml_renderer = XMLRenderer()
        xml_output_path = output_dir / f"{base_name}_ccd.xml"
        xml_content = xml_renderer.render(medical_document)
        with open(xml_output_path, "w", encoding="utf-8") as f:
            f.write(xml_content)

        # PDF (Human-readable)
        pdf_renderer = PDFRenderer()
        pdf_output_path = output_dir / f"{base_name}_report.pdf"
        pdf_renderer.render(medical_document, str(pdf_output_path))

        # DOCX (Editable)
        docx_renderer = DOCXRenderer()
        docx_output_path = output_dir / f"{base_name}_report.docx"
        docx_renderer.render(medical_document, str(docx_output_path))

        # Complete
        progress_bar.progress(100)
        status_text.text("✅ Processing complete!")

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

    except Exception as e:
        logger.error(f"Processing failed: {e}", exc_info=True)
        raise
    finally:
        # Cleanup temp file
        if temp_input_path.exists():
            temp_input_path.unlink()


def main():
    """Main Streamlit app"""

    # Header
    st.markdown('<div class="main-header">🏥 Medical PDF → CCD/CCDA Converter</div>',
                unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Enterprise-grade OCR with LLM-based XML generation</div>',
                unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        st.header("ℹ️ About")
        st.markdown("""
        This system converts medical PDFs to structured CCD/CCDA XML format using:

        **🔍 OCR**: Gemini 3 Pro Preview
        **🧠 Structuring**: Gemini 2.5 Flash
        **📝 XML Generation**: LLM-based with raw OCR text

        **Enterprise Features:**
        - ✅ Honest confidence scoring
        - ✅ Source text traceability
        - ✅ Explainable deduplication
        - ✅ Practice Fusion CDA R2.1 compliance
        """)

        st.header("⚙️ Settings")

        # Check for API key
        try:
            config = get_config()
            if config.gemini_api_key:
                st.success("✅ Gemini API key configured")
            else:
                st.error("❌ Gemini API key not found")
                st.info("Add GEMINI_API_KEY to .env file")
        except Exception as e:
            st.error(f"❌ Configuration error: {e}")

    # Main content
    tab1, tab2, tab3 = st.tabs(["📤 Upload & Process", "📊 View Results", "📖 Documentation"])

    with tab1:
        st.header("Upload Medical PDF")

        uploaded_file = st.file_uploader(
            "Choose a medical PDF file",
            type=['pdf'],
            help="Upload a medical document (handwritten or printed)"
        )

        if uploaded_file:
            col1, col2 = st.columns([2, 1])

            with col1:
                st.info(f"📄 **File:** {uploaded_file.name}")
                st.info(f"📏 **Size:** {uploaded_file.size / 1024:.2f} KB")

            with col2:
                process_button = st.button("🚀 Process Document", type="primary", use_container_width=True)

            if process_button:
                # Create output directory with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_dir = Path(__file__).parent / "outputs" / f"{timestamp}_{uploaded_file.name.split('.')[0]}"
                output_dir.mkdir(parents=True, exist_ok=True)

                try:
                    with st.spinner("Processing medical document..."):
                        result = process_medical_pdf(uploaded_file, output_dir)

                    if result["success"]:
                        st.markdown('<div class="success-box">✅ <strong>Processing completed successfully!</strong></div>',
                                   unsafe_allow_html=True)

                        # Display metrics
                        st.subheader("📊 Processing Metrics")
                        col1, col2, col3, col4 = st.columns(4)

                        with col1:
                            st.metric("Pages Processed", result["metadata"]["pages"])
                        with col2:
                            st.metric("Visits Detected", result["metadata"]["visits"])
                        with col3:
                            st.metric("OCR Confidence", f"{result['metadata']['confidence']:.1%}")
                        with col4:
                            st.metric("Processing Time", f"{result['metadata']['processing_time_ms']/1000:.1f}s")

                        # Download buttons
                        st.subheader("📥 Download Results")

                        col1, col2, col3 = st.columns(3)

                        with col1:
                            with open(result["xml_file"], "r", encoding="utf-8") as f:
                                st.download_button(
                                    "⬇️ Download CCD/CCDA XML",
                                    f.read(),
                                    file_name=f"{result['base_name']}_ccd.xml",
                                    mime="text/xml"
                                )

                        with col2:
                            with open(result["pdf_file"], "rb") as f:
                                st.download_button(
                                    "⬇️ Download PDF Report",
                                    f.read(),
                                    file_name=f"{result['base_name']}_report.pdf",
                                    mime="application/pdf"
                                )

                        with col3:
                            with open(result["docx_file"], "rb") as f:
                                st.download_button(
                                    "⬇️ Download DOCX Report",
                                    f.read(),
                                    file_name=f"{result['base_name']}_report.docx",
                                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                                )

                        # Additional files
                        with st.expander("📂 Additional Files"):
                            col1, col2 = st.columns(2)

                            with col1:
                                with open(result["canonical_json"], "r", encoding="utf-8") as f:
                                    st.download_button(
                                        "⬇️ Canonical JSON",
                                        f.read(),
                                        file_name=f"{result['base_name']}_canonical.json",
                                        mime="application/json"
                                    )

                            with col2:
                                with open(result["ocr_file"], "r", encoding="utf-8") as f:
                                    st.download_button(
                                        "⬇️ Raw OCR Text",
                                        f.read(),
                                        file_name=f"{result['base_name']}_ocr.txt",
                                        mime="text/plain"
                                    )

                        # Preview
                        st.subheader("👁️ Preview CCD/CCDA XML")
                        with open(result["xml_file"], "r", encoding="utf-8") as f:
                            xml_preview = f.read()
                            st.code(xml_preview[:2000] + "\n\n... (truncated, download full file)", language="xml")

                        # Save to session state for viewing in Results tab
                        st.session_state['last_result'] = result

                except Exception as e:
                    st.markdown(f'<div class="error-box">❌ <strong>Processing failed:</strong> {str(e)}</div>',
                               unsafe_allow_html=True)
                    st.exception(e)

    with tab2:
        st.header("View Previous Results")

        if 'last_result' in st.session_state:
            result = st.session_state['last_result']

            st.success(f"✅ Last processed: **{result['base_name']}**")

            # Display canonical JSON
            st.subheader("📋 Canonical JSON Data")
            with open(result["canonical_json"], "r", encoding="utf-8") as f:
                canonical_data = json.load(f)
                st.json(canonical_data)

            # Display OCR confidence details
            if canonical_data.get('visits'):
                st.subheader("🔍 Visit Details")
                for idx, visit in enumerate(canonical_data['visits'], 1):
                    with st.expander(f"Visit {idx}: {visit.get('visit_date', 'N/A')}"):
                        st.write(f"**Visit ID:** {visit.get('visit_id')}")
                        st.write(f"**Reason for Visit:** {visit.get('reason_for_visit', 'N/A')}")
                        st.write(f"**Medications:** {len(visit.get('medications', []))}")
                        st.write(f"**Problems:** {len(visit.get('problem_list', []))}")
                        st.write(f"**Results:** {len(visit.get('results', []))}")
                        st.write(f"**Source Pages:** {visit.get('raw_source_pages', [])}")
        else:
            st.info("👆 Process a document first to view results here")

    with tab3:
        st.header("Documentation")

        st.markdown("""
        ### 🚀 Quick Start

        1. **Upload** a medical PDF (handwritten or printed)
        2. **Click** "Process Document"
        3. **Download** your CCD/CCDA XML and reports

        ### 📋 Output Files

        | File | Description |
        |------|-------------|
        | `*_ccd.xml` | CCD/CCDA R2.1 compliant XML (LLM-generated from raw OCR) |
        | `*_report.pdf` | Human-readable summary report |
        | `*_report.docx` | Editable Word document |
        | `*_canonical.json` | Structured JSON (source of truth) |
        | `*_ocr.txt` | Raw OCR text from all pages |

        ### ✨ Enterprise Features

        #### 1. Honest Confidence Scoring
        - Realistic 60-85% OCR confidence (not false 100%)
        - Tracks uncertain tokens with line numbers
        - Flags documents for manual review when needed

        #### 2. Source Text Traceability
        - Every data point includes `source_page`, `source_line`, and `source_excerpt`
        - Full audit trail from OCR to structured output
        - Easy verification of extracted data

        #### 3. Explainable Deduplication
        - Rule-based merging with clear reasoning
        - Levenshtein distance similarity scores (85% threshold)
        - Complete merge log with mathematical justification

        #### 4. LLM-Based XML Generation
        - Uses raw OCR text (not simplified JSON) for maximum context
        - Generates both narrative text AND structured entries
        - Preserves clinical uncertainty markers (?, R/O, [UNCLEAR])
        - No medical code guessing - only uses confirmed codes

        ### 🔧 System Architecture

        ```
        PDF Input
            ↓
        OCR (Gemini 3 Pro) → Raw Text + Confidence
            ↓
        Chunking → Visit Detection
            ↓
        Structuring (Gemini 2.5 Flash) → Canonical JSON + Raw OCR
            ↓
        Deduplication → Merged Data
            ↓
        LLM Renderer (Raw OCR → XML) → CCD/CCDA XML
            ↓
        PDF/DOCX Renderers → Human-Readable Reports
        ```

        ### 📞 Support

        For issues or questions:
        - Check the logs in the output directory
        - Verify your Gemini API key is configured
        - Ensure input PDFs are valid medical documents

        ### 📄 License

        Enterprise Medical AI System - © 2025
        """)


if __name__ == "__main__":
    main()
