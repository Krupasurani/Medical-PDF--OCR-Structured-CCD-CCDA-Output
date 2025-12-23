# 🏥 Medical PDF → CCD/CCDA Converter

**Enterprise-grade medical document OCR with LLM-based XML generation**

Convert handwritten and printed medical PDFs to structured CCD/CCDA R2.1 compliant XML using AI-powered OCR and intelligent structuring.

---

## ✨ Features

### Core Capabilities
- 🔍 **Advanced OCR**: Gemini 3 Pro Preview for handwritten + printed text
- 🧠 **AI Structuring**: Gemini 2.5 Flash for medical data extraction
- 📝 **LLM-based XML**: Uses raw OCR text for accurate CCD/CCDA generation
- 🎨 **Web UI**: Beautiful Streamlit interface for easy document processing

### Enterprise Features
✅ **Honest Confidence Scoring** (60-85% realistic range, not false 100%)
✅ **Source Text Traceability** (line numbers + excerpts for all data)
✅ **Explainable Deduplication** (rule-based with similarity scores)
✅ **Practice Fusion CDA R2.1 Compliance** (proper template structure)

---

## 🚀 Quick Start

### 1. Installation

```bash
# Clone or navigate to final_system directory
cd final_system

# Install dependencies
pip install -r requirements.txt

# For Windows users (PDF processing)
# Download and install Poppler: https://github.com/oschwartz10612/poppler-windows/releases
```

### 2. Configuration

Create a `.env` file in the `final_system` directory:

```env
# Required: Google Gemini API Key
GEMINI_API_KEY=your_gemini_api_key_here

# Optional: Model names (defaults shown)
OCR_MODEL_NAME=gemini-3-pro-preview
STRUCTURING_MODEL_NAME=gemini-2.5-flash

# Optional: Debug mode
DEBUG=false
```

**Get your Gemini API key:**
1. Go to https://makersuite.google.com/app/apikey
2. Create a new API key
3. Copy and paste into `.env` file

### 3. Run the Application

```bash
# Start the web UI
streamlit run app.py
```

The application will open in your browser at `http://localhost:8501`

---

## 📖 Usage

### Via Web UI (Recommended)

1. **Upload PDF**: Click "Browse files" and select your medical PDF
2. **Process**: Click "🚀 Process Document"
3. **Download**: Get your CCD/CCDA XML, PDF report, and DOCX files
4. **Review**: Check metrics and preview results

### Via Command Line

```bash
# Process a single document
python -c "
from pathlib import Path
from app.services.pdf_service import PDFService
from app.services.ocr_service import OCRService
from app.services.structuring_service import StructuringService
from app.renderers import XMLRenderer

# Your processing code here
"
```

---

## 📂 Output Files

For each processed document, you'll get:

| File | Description |
|------|-------------|
| `*_ccd.xml` | **CCD/CCDA R2.1 XML** - Standards-compliant XML generated from raw OCR text |
| `*_report.pdf` | **Human-Readable PDF** - Formatted clinical summary (Specialist Consult style) |
| `*_report.docx` | **Editable DOCX** - Microsoft Word format for editing |
| `*_canonical.json` | **Canonical JSON** - Structured data (single source of truth) |
| `*_ocr.txt` | **Raw OCR Text** - Complete OCR output from all pages |

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     PDF Input Document                       │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│  Step 1: OCR (Gemini 3 Pro Preview)                         │
│  • Extract printed + handwritten text                        │
│  • Realistic confidence scoring (60-85%)                     │
│  • Mark unclear sections with [UNCLEAR]                      │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│  Step 2: Chunking (Visit Detection)                         │
│  • Detect clinical visit boundaries                          │
│  • Preserve page-level context                               │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│  Step 3: Structuring (Gemini 2.5 Flash)                     │
│  • Extract medications, problems, results, plan              │
│  • Add source_page, source_line, source_excerpt              │
│  • Store raw OCR text for LLM rendering                      │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│  Step 4: Deduplication                                       │
│  • Fuzzy matching with 85% threshold                         │
│  • Explainable merge logs with similarity scores             │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│  Step 5: LLM-Based XML Rendering                            │
│  • Input: Raw OCR text (complete context)                    │
│  • Generate: CCD/CCDA R2.1 XML with narrative + entries     │
│  • Preserve: Clinical uncertainty (??, R/O, [UNCLEAR])      │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│  Step 6: Human-Readable Rendering                           │
│  • PDF: Specialist Consult Summary format                    │
│  • DOCX: Editable Microsoft Word document                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔬 Technical Details

### LLM-Based XML Generation

**Why Raw OCR Text?**
- **More Context**: LLM sees complete original text, not just extracted fields
- **Better Accuracy**: Preserves formatting, layout, and visual context
- **Nuance Preservation**: Keeps clinical uncertainty markers and handwritten notes exactly as written

**Process:**
```
Raw OCR Text (all pages) → Detailed CCD/CCDA Prompt → Gemini 2.5 Flash
    ↓
CCD/CCDA R2.1 XML with:
  • Proper namespaces (hl7, xsi, sdtc)
  • Author and Custodian sections
  • Narrative <text> blocks
  • Structured <entry> elements
  • SNOMED/LOINC codes (when available)
  • Preserved uncertainty markers
```

### Honest Confidence Scoring

Instead of unrealistic 100% confidence, the system provides:

```python
Base Confidence: 70%  # Realistic for medical notes

Penalties:
- [UNCLEAR] markers:      -15% each
- Handwriting indicators: -5% each
- Ambiguous characters:   -8% if >15% of text
- Medical abbreviations:  -5% if >5 detected

Maximum: 85%  # Cap for best-case scenarios
```

### Source Traceability

Every extracted data point includes:
```json
{
  "name": "Metformin 500mg",
  "source_page": 2,
  "source_line": 15,
  "source_excerpt": "Medications: Metformin 500mg BID po"
}
```

---

## 🛠️ Troubleshooting

### Common Issues

**"No module named 'app'"**
```bash
# Make sure you're in the final_system directory
cd final_system
streamlit run app.py
```

**"Gemini API key not found"**
```bash
# Create or update .env file
echo "GEMINI_API_KEY=your_key_here" > .env
```

**PDF processing fails on Windows**
```bash
# Install Poppler for Windows
# Download from: https://github.com/oschwartz10612/poppler-windows/releases
# Add bin directory to PATH
```

**Import errors**
```bash
# Reinstall dependencies
pip install --force-reinstall -r requirements.txt
```

---

## 📊 Performance

Typical processing times (5-page document):
- OCR: ~30-40 seconds
- Structuring: ~15-20 seconds
- Rendering: ~5 seconds
- **Total: ~50-65 seconds**

---

## 🔐 Security & Privacy

- ✅ All processing happens via Google Gemini API
- ✅ Uploaded files are temporarily stored and deleted after processing
- ✅ No data is permanently stored on servers
- ✅ HIPAA considerations: Review Google Gemini's BAA before production use

---

## 📋 System Requirements

- **Python**: 3.9 or higher
- **RAM**: 2GB minimum, 4GB recommended
- **Disk**: 500MB for dependencies
- **Internet**: Required for Gemini API calls
- **OS**: Windows, macOS, or Linux

---

## 🤝 Contributing

This is an enterprise medical AI system. For modifications:
1. Test thoroughly with sample medical documents
2. Validate XML output against CCD/CCDA validators
3. Ensure HIPAA compliance considerations

---

## 📄 License

Enterprise Medical AI System - © 2025

---

## 🆘 Support

### Documentation
- See the **"Documentation"** tab in the web UI for detailed info
- Check `outputs/` directory for processing logs

### API Keys
- Gemini API: https://makersuite.google.com/app/apikey

### Issues
- Review error messages in the UI
- Check terminal logs for detailed stack traces
- Verify .env configuration

---

## 🎯 Next Steps

1. ✅ Install dependencies
2. ✅ Configure Gemini API key
3. ✅ Run `streamlit run app.py`
4. ✅ Upload a medical PDF
5. ✅ Download your CCD/CCDA XML!

**Ready to process medical documents with enterprise-grade AI!** 🚀
