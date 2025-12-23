"""
Medical PDF OCR to CCD/CCDA Converter - Streamlit Web UI
Simple one-page interface with token tracking
"""

import streamlit as st
import os
import sys
import time
import zipfile
import shutil
from pathlib import Path
from datetime import datetime
import tempfile

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
    page_title="Medical PDF → CCD/CCDA",
    page_icon="🏥",
    layout="centered"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .stButton button {
        width: 100%;
        background-color: #1f77b4;
        color: white;
        font-size: 1.2rem;
        padding: 0.75rem;
        border-radius: 0.5rem;
    }
    .success-box {
        background: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)


def process_medical_pdf(uploaded_file, output_dir: Path):
    """Process medical PDF and track tokens"""

    start_time = time.time()

    # Initialize token tracking
    token_usage = {
        "ocr": {"input": 0, "output": 0, "calls": 0},
        "structuring": {"input": 0, "output": 0, "calls": 0},
        "xml_llm": {"input": 0, "output": 0, "calls": 0},
        "pdf_llm": {"input": 0, "output": 0, "calls": 0},
    }

    # Save uploaded file
    temp_input = output_dir / "temp_input.pdf"
    with open(temp_input, "wb") as f:
        f.write(uploaded_file.getbuffer())

    base_name = Path(uploaded_file.name).stem.replace(" ", "_")

    progress_bar = st.progress(0)
    status_text = st.empty()

    try:
        # Step 1: PDF Validation (5%)
        status_text.text("📄 Validating PDF...")
        progress_bar.progress(5)

        pdf_service = PDFService()
        pdf_data = pdf_service.process_pdf(str(temp_input))

        # Step 2: OCR (40%)
        total_pages = pdf_data['metadata']['page_count']
        status_text.text(f"🔍 OCR Processing ({total_pages} pages)...")
        progress_bar.progress(10)

        # Progress callback for OCR
        def ocr_progress_callback(page_num, total):
            progress = 10 + int(30 * page_num / total)  # 10% to 40%
            progress_bar.progress(progress)
            status_text.text(f"🔍 OCR Processing page {page_num}/{total}...")

        ocr_service = OCRService()
        ocr_results = ocr_service.process_pages(pdf_data["images"], progress_callback=ocr_progress_callback)

        # Track OCR tokens (estimate based on text length)
        for result in ocr_results:
            text_len = len(result.get("raw_text", ""))
            token_usage["ocr"]["output"] += text_len // 4  # ~4 chars per token
            token_usage["ocr"]["calls"] += 1

        progress_bar.progress(40)

        # Save OCR
        ocr_file = output_dir / f"{base_name}_ocr.txt"
        with open(ocr_file, "w", encoding="utf-8") as f:
            for result in ocr_results:
                f.write(f"\n{'=' * 80}\nPAGE {result['page_number']}\n{'=' * 80}\n\n")
                f.write(result["raw_text"])
                f.write("\n\n")

        # Step 3: Chunking (50%)
        status_text.text("📊 Detecting visits...")
        progress_bar.progress(50)

        chunking_service = ChunkingService()
        chunks = chunking_service.chunk_pages(ocr_results)

        # Step 4: Structuring (70%)
        status_text.text("🧠 Structuring medical data...")
        progress_bar.progress(60)

        structuring_service = StructuringService()
        medical_document = structuring_service.structure_document(chunks, ocr_results)

        # Track structuring tokens
        for chunk in chunks:
            text_len = len(chunk.get("raw_text", ""))
            token_usage["structuring"]["input"] += text_len // 4
            token_usage["structuring"]["calls"] += 1

        medical_document.processing_duration_ms = int((time.time() - start_time) * 1000)

        progress_bar.progress(70)

        # Step 5: Deduplication (75%)
        status_text.text("🔄 Removing duplicates...")
        progress_bar.progress(75)

        dedup_service = DeduplicationService(fuzzy_threshold=0.85)
        deduplicated = dedup_service.deduplicate_document(
            [v.model_dump() if hasattr(v, 'model_dump') else v for v in medical_document.visits]
        )
        medical_document.visits = deduplicated

        # Step 6: Save JSON (80%)
        status_text.text("💾 Saving canonical JSON...")
        progress_bar.progress(80)

        json_file = output_dir / f"{base_name}_canonical.json"
        with open(json_file, "w", encoding="utf-8") as f:
            f.write(medical_document.model_dump_json())

        # Step 7: Render outputs (95%)
        status_text.text("📝 Generating XML, PDF, DOCX...")
        progress_bar.progress(85)

        # XML (LLM-based)
        xml_renderer = XMLRenderer()
        xml_file = output_dir / f"{base_name}_ccd.xml"
        xml_content = xml_renderer.render(medical_document)
        with open(xml_file, "w", encoding="utf-8") as f:
            f.write(xml_content)

        # Track XML LLM tokens
        if medical_document.raw_ocr_text:
            token_usage["xml_llm"]["input"] += len(medical_document.raw_ocr_text) // 4
            token_usage["xml_llm"]["output"] += len(xml_content) // 4
            token_usage["xml_llm"]["calls"] += 1

        progress_bar.progress(90)

        # PDF (LLM-based)
        pdf_renderer = PDFRenderer()
        pdf_file = output_dir / f"{base_name}_report.pdf"
        pdf_renderer.render(medical_document, str(pdf_file))

        # Track PDF LLM tokens
        if medical_document.raw_ocr_text:
            token_usage["pdf_llm"]["input"] += len(medical_document.raw_ocr_text) // 4
            token_usage["pdf_llm"]["calls"] += 1

        # DOCX
        docx_renderer = DOCXRenderer()
        docx_file = output_dir / f"{base_name}_report.docx"
        docx_renderer.render(medical_document, str(docx_file))

        progress_bar.progress(100)
        status_text.text("✅ Processing complete!")

        # Calculate totals
        total_tokens = {
            "input": sum(v["input"] for v in token_usage.values()),
            "output": sum(v["output"] for v in token_usage.values()),
            "total": sum(v["input"] + v["output"] for v in token_usage.values()),
        }

        return {
            "success": True,
            "base_name": base_name,
            "files": {
                "json": json_file,
                "ocr": ocr_file,
                "xml": xml_file,
                "pdf": pdf_file,
                "docx": docx_file,
            },
            "metadata": {
                "pages": medical_document.page_count,
                "visits": len(medical_document.visits),
                "confidence": medical_document.ocr_confidence_avg,
                "processing_time_ms": medical_document.processing_duration_ms,
            },
            "token_usage": token_usage,
            "total_tokens": total_tokens,
        }

    finally:
        if temp_input.exists():
            temp_input.unlink()


def create_download_zip(output_dir: Path, base_name: str) -> Path:
    """Create zip file with all outputs"""
    zip_path = output_dir / f"{base_name}_complete.zip"

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in output_dir.glob(f"{base_name}*"):
            if file != zip_path and not file.name.startswith("temp_"):
                zipf.write(file, file.name)

    return zip_path


def main():
    """Main application"""

    # Header
    st.markdown('<div class="main-header">🏥 Medical PDF → CCD/CCDA Converter</div>',
                unsafe_allow_html=True)
    st.markdown("**Enterprise-grade OCR with LLM-based XML generation**")

    # Check API key
    try:
        config = get_config()
        if not config.gemini_api_key:
            st.error("❌ Gemini API key not configured. Add GEMINI_API_KEY to .env file")
            st.stop()
    except Exception as e:
        st.error(f"❌ Configuration error: {e}")
        st.stop()

    st.markdown("---")

    # File upload
    uploaded_file = st.file_uploader(
        "📤 Upload Medical PDF",
        type=['pdf'],
        help="Upload handwritten or printed medical document"
    )

    if uploaded_file:
        # Show file info
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"**File:** {uploaded_file.name}")
        with col2:
            st.info(f"**Size:** {uploaded_file.size / 1024:.2f} KB")

        # Process button
        if st.button("🚀 Process Document", type="primary"):
            # Create output directory
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = Path("outputs") / f"{timestamp}_{Path(uploaded_file.name).stem}"
            output_dir.mkdir(parents=True, exist_ok=True)

            with st.spinner("Processing medical document..."):
                try:
                    result = process_medical_pdf(uploaded_file, output_dir)

                    if result["success"]:
                        st.markdown('<div class="success-box">✅ <strong>Processing completed successfully!</strong></div>',
                                   unsafe_allow_html=True)

                        # Metrics
                        st.subheader("📊 Processing Metrics")
                        col1, col2, col3, col4 = st.columns(4)

                        with col1:
                            st.metric("Pages", result["metadata"]["pages"])
                        with col2:
                            st.metric("Visits", result["metadata"]["visits"])
                        with col3:
                            st.metric("Confidence", f"{result['metadata']['confidence']:.0%}")
                        with col4:
                            st.metric("Time", f"{result['metadata']['processing_time_ms']/1000:.1f}s")

                        # Token usage (debug)
                        with st.expander("🔍 Token Usage & Cost Estimation"):
                            st.write("**Token Usage by Model:**")

                            for model, usage in result["token_usage"].items():
                                if usage["calls"] > 0:
                                    st.write(f"**{model.upper()}:**")
                                    st.write(f"  - Calls: {usage['calls']}")
                                    st.write(f"  - Input tokens: {usage['input']:,}")
                                    st.write(f"  - Output tokens: {usage['output']:,}")
                                    st.write(f"  - Total: {usage['input'] + usage['output']:,}")
                                    st.write("")

                            st.write("**TOTAL TOKENS:**")
                            st.write(f"  - Input: {result['total_tokens']['input']:,}")
                            st.write(f"  - Output: {result['total_tokens']['output']:,}")
                            st.write(f"  - **Total: {result['total_tokens']['total']:,}**")

                            # Cost estimation (Gemini pricing as of Dec 2024)
                            cost_input = (result['total_tokens']['input'] / 1_000_000) * 0.075
                            cost_output = (result['total_tokens']['output'] / 1_000_000) * 0.30
                            total_cost = cost_input + cost_output

                            st.write("")
                            st.write("**Estimated Cost (Gemini Flash):**")
                            st.write(f"  - Input: ${cost_input:.4f}")
                            st.write(f"  - Output: ${cost_output:.4f}")
                            st.write(f"  - **Total: ${total_cost:.4f}**")

                        st.markdown("---")

                        # Download all button
                        st.subheader("📥 Download Results")

                        zip_file = create_download_zip(output_dir, result["base_name"])

                        with open(zip_file, "rb") as f:
                            st.download_button(
                                "⬇️ Download All Files (ZIP)",
                                f.read(),
                                file_name=f"{result['base_name']}_complete.zip",
                                mime="application/zip",
                                use_container_width=True
                            )

                        # Individual downloads
                        with st.expander("Download Individual Files"):
                            col1, col2 = st.columns(2)

                            with col1:
                                with open(result["files"]["xml"], "r") as f:
                                    st.download_button(
                                        "📄 CCD/CCDA XML",
                                        f.read(),
                                        file_name=f"{result['base_name']}_ccd.xml",
                                        mime="text/xml"
                                    )

                                with open(result["files"]["json"], "r") as f:
                                    st.download_button(
                                        "📋 Canonical JSON",
                                        f.read(),
                                        file_name=f"{result['base_name']}_canonical.json",
                                        mime="application/json"
                                    )

                            with col2:
                                with open(result["files"]["pdf"], "rb") as f:
                                    st.download_button(
                                        "📕 PDF Report",
                                        f.read(),
                                        file_name=f"{result['base_name']}_report.pdf",
                                        mime="application/pdf"
                                    )

                                with open(result["files"]["ocr"], "r") as f:
                                    st.download_button(
                                        "📃 Raw OCR Text",
                                        f.read(),
                                        file_name=f"{result['base_name']}_ocr.txt",
                                        mime="text/plain"
                                    )

                        st.success(f"✅ All files saved to: `{output_dir}`")

                except Exception as e:
                    st.error(f"❌ Processing failed: {str(e)}")
                    st.exception(e)


if __name__ == "__main__":
    main()
