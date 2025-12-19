# ARCHITECTURE.md

## System Overview

This system converts scanned medical PDFs into structured clinical documents using a **local, deterministic AI pipeline**.

The architecture follows a strict separation of concerns:
- **OCR extraction** (vision-based)
- **Medical structuring** (LLM-based)
- **Rendering** (template-based)

**No logic is duplicated across stages.**

---

## High-Level Flow

```
PDF
  ↓
Vision OCR (Gemini 3 Preview)
  ↓
Raw OCR Pages
  ↓
Chunking & Structuring (Gemini 2.5 Flash)
  ↓
Canonical JSON
  ↓
  ├── XML Renderer (CCD/CCDA-style)
  └── Human-Readable Renderer (HTML → PDF/DOCX)
```

---

## Core Principles

1. **JSON is the single source of truth**
2. **No hallucination or inference**
3. **Deterministic output** (same input → same output)
4. **Explicit uncertainty handling** (`[UNCLEAR]` markers)
5. **API-ready but local-only deployment**

---

## Component Architecture

### 1. Input Layer

**Responsibilities:**
- Accept PDF files only
- Validate:
  - File size (max 50MB)
  - Page count (max 100 pages)
  - PDF integrity
- No persistent storage

**Technology:**
- `pypdf` for PDF parsing
- `pdf2image` for page extraction

---

### 2. OCR Layer (Vision-Based)

**Model:** Gemini 3 Preview

**Responsibilities:**
- Page-by-page text extraction
- Preserve original text exactly (no correction)
- Detect unreadable content
- Output raw OCR text with confidence score

**Input:**
```python
{
  "pdf_path": "path/to/file.pdf",
  "page_number": 1
}
```

**Output:**
```json
{
  "page_number": 1,
  "raw_text": "...",
  "confidence_score": 0.95
}
```

**No correction or interpretation occurs here.**

---

### 3. Chunking & Structuring Layer

**Model:** Gemini 2.5 Flash

**Responsibilities:**
- Group OCR text by visit/encounter/date
- Populate canonical JSON schema
- Track source page references for all data
- Flag ambiguous or incomplete data
- Merge duplicate entries (exact + fuzzy matching)

**Input:**
```python
{
  "ocr_pages": [
    {"page_number": 1, "raw_text": "..."},
    {"page_number": 2, "raw_text": "..."}
  ]
}
```

**Output:** Canonical JSON (see schema below)

**This layer applies structure, not medical judgment.**

---

### 4. Canonical Data Layer (JSON)

**Purpose:** Single authoritative representation of medical document

**Schema:** Version 2.0

**Key sections:**
- `document_metadata` - Patient demographics, document info
- `visits[]` - Array of clinical encounters
  - `medications[]`
  - `vital_signs{}`
  - `problem_list[]`
  - `results[]` (lab values, diagnostics)
  - `assessment`
  - `plan[]`
- `data_quality` - Confidence scores, warnings, unclear sections

**All downstream outputs derive from this JSON.**

**Schema file:** `schemas/canonical_v2.0.json`

---

### 5. Rendering Layer

#### XML Renderer

**Purpose:** Generate CCD/CCDA-style XML

**Method:**
- Jinja2 templates
- All data from canonical JSON
- No extraction logic

**Output:** Standards-aligned XML (HL7 CCD format)

#### Human-Readable Renderer

**Purpose:** Generate clinical narrative document

**Method:**
- HTML template (Jinja2)
- Export to PDF (reportlab) or DOCX (python-docx)
- Professional medical document styling

**Output:** PDF or DOCX file

**Both renderers are pure transformation layers - no additional data processing.**

---

### 6. UI Layer

**Framework:** Streamlit (local web interface)

**Features:**
- Upload PDF file
- Real-time processing progress
- Display warnings and confidence scores
- Download outputs:
  - Canonical JSON
  - CCD XML
  - Human-readable PDF/DOCX

**Constraints:**
- No authentication (single-user)
- No external exposure (localhost only)
- No data persistence (session-based)

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────┐
│                      User / Client                       │
└─────────────────────────────────────────────────────────┘
                            ↓
                   ┌────────────────┐
                   │  Streamlit UI  │
                   └────────────────┘
                            ↓
              ┌─────────────────────────┐
              │   PDF Validation        │
              │   (size, format, pages) │
              └─────────────────────────┘
                            ↓
        ┌───────────────────────────────────────┐
        │   OCR Service (Gemini 3 Preview)      │
        │   • Page-by-page extraction           │
        │   • Confidence scoring                │
        └───────────────────────────────────────┘
                            ↓
              ┌─────────────────────────┐
              │   OCR Cache (memory)    │
              │   [page_1, page_2, ...] │
              └─────────────────────────┘
                            ↓
        ┌───────────────────────────────────────┐
        │  Structuring Service                  │
        │  (Gemini 2.5 Flash)                   │
        │  • Visit chunking                     │
        │  • Schema population                  │
        │  • Deduplication                      │
        └───────────────────────────────────────┘
                            ↓
              ┌─────────────────────────┐
              │   Canonical JSON        │
              │   (single source)       │
              └─────────────────────────┘
                            ↓
                   ┌────────┴────────┐
                   ↓                 ↓
        ┌──────────────────┐  ┌─────────────────┐
        │  XML Renderer    │  │ Human-Readable  │
        │  (template)      │  │ Renderer        │
        └──────────────────┘  └─────────────────┘
                   ↓                 ↓
        ┌──────────────────┐  ┌─────────────────┐
        │   CCD XML File   │  │   PDF/DOCX      │
        └──────────────────┘  └─────────────────┘
                            ↓
                   ┌────────────────┐
                   │  Download to   │
                   │     User       │
                   └────────────────┘
```

---

## Technology Stack

### Core Dependencies

**PDF Processing:**
- `pypdf==4.0.1` - PDF parsing
- `pdf2image==1.17.0` - Page image extraction
- `Pillow==10.2.0` - Image handling

**AI/ML:**
- `google-generativeai==0.3.2` - Gemini API client

**Data Validation:**
- `pydantic==2.5.3` - Schema validation
- `jsonschema==4.20.0` - JSON schema validation

**Rendering:**
- `lxml==5.1.0` - XML processing
- `jinja2==3.1.3` - Templating
- `reportlab==4.0.9` - PDF generation
- `python-docx==1.1.0` - DOCX generation

**UI:**
- `streamlit==1.30.0` - Web interface

**Utilities:**
- `python-dateutil==2.8.2` - Date parsing
- `python-dotenv==1.0.1` - Environment variables
- `tenacity==8.2.3` - Retry logic

### Python Version
- **Minimum:** Python 3.10
- **Recommended:** Python 3.11

---

## Security & Privacy

### Data Handling
- ✅ **Local-only execution** (no cloud storage)
- ✅ **In-memory processing** (files not persisted)
- ✅ **Temporary file cleanup** (automatic after processing)
- ✅ **No logging of PHI** (configurable)

### API Security
- ✅ **API keys in environment variables** (never in code)
- ✅ **HTTPS for Gemini API calls**
- ✅ **No data sharing** (Gemini API: data not used for training per Google Cloud terms)

### Deployment
- ✅ **Localhost binding only** (`127.0.0.1`)
- ✅ **No network exposure**
- ✅ **No authentication required** (single-user assumption)

**Note:** While this system follows HIPAA-aligned practices (minimum necessary data, audit logging, secure disposal), it is **not certified as HIPAA-compliant**. Consult legal/compliance before use in production healthcare environments.

---

## Error Handling

### Philosophy
- **Fail loudly** - No silent failures
- **Partial results** - Return what was successfully extracted
- **Clear errors** - User-friendly error messages
- **Traceability** - Log errors with context

### Error Categories

| Error Type | Handling | User Experience |
|------------|----------|----------------|
| Invalid PDF | Reject upload | "PDF file is corrupted or invalid" |
| File too large | Reject upload | "File exceeds 50MB limit" |
| OCR failure | Retry 3x, then partial results | "OCR failed for page 3, continuing..." |
| API timeout | Retry with backoff | "Processing delayed, retrying..." |
| Schema validation | Accept with warnings | "Output may be incomplete, see warnings" |
| No text detected | Return empty JSON | "No text detected in document" |

### Retry Logic

```python
# Exponential backoff for API calls
MAX_RETRIES = 3
BACKOFF_MULTIPLIER = 2
INITIAL_DELAY = 1  # seconds

# Retry on: timeout, rate limit, 5xx errors
# Fail immediately on: 4xx errors (except 429)
```

---

## Performance Characteristics

### Processing Time (Estimates)

| Document Size | OCR Time | Total Processing |
|---------------|----------|------------------|
| 1-5 pages     | <30s     | <60s             |
| 6-20 pages    | <90s     | <3 minutes       |
| 21-50 pages   | <3 min   | <6 minutes       |
| 51-100 pages  | <6 min   | <12 minutes      |

**Note:** Times assume reasonable quality scans (200+ DPI) and normal API latency.

### Resource Usage

**Memory:**
- Peak usage: ~2GB per document
- Streaming processing for large files

**Disk:**
- Temporary storage: ~2x file size
- Auto-cleanup after processing

**API Rate Limits (Gemini):**
- Monitor quota usage
- Implement backoff on 429 responses

---

## API Readiness (Future)

While no APIs are exposed in Phase 1, the architecture is designed for easy REST API wrapping:

**Modular Services:**
```python
# Core services are stateless functions
ocr_service.extract_text(pdf_path) → OCR result
structuring_service.structure(ocr_pages) → JSON
rendering_service.render_xml(json) → XML
rendering_service.render_pdf(json) → PDF
```

**Future API Endpoints (Phase 2):**
```
POST /api/v1/process
  - Body: PDF file (multipart/form-data)
  - Response: Job ID

GET /api/v1/jobs/{job_id}
  - Response: Processing status + results

GET /api/v1/jobs/{job_id}/outputs/{type}
  - type: json | xml | pdf | docx
  - Response: File download
```

**No changes to core logic required - only add FastAPI wrapper.**

---

## Testing Strategy

### Unit Tests
- Schema validation
- Deduplication logic
- Date parsing
- Error handling
- Template rendering

### Integration Tests
- OCR → Structuring pipeline
- JSON → XML conversion
- JSON → PDF conversion
- Error propagation

### End-to-End Tests
- Process real medical PDFs
- Validate outputs against expected structure
- Performance benchmarks

**Test Framework:** pytest

---

## Limitations & Constraints

### Current Scope (Phase 1)
- ✅ Local deployment only
- ✅ Single-user operation
- ✅ No authentication
- ✅ No persistent storage
- ✅ Basic CCD/CCDA XML (not full FHIR)

### Explicitly Out of Scope
- ❌ Cloud deployment
- ❌ Multi-user support
- ❌ Public API exposure
- ❌ Clinical decision support
- ❌ Medical code validation (ICD-10, CPT)
- ❌ EHR system integration
- ❌ Real-time processing

### Known Edge Cases
- **Handwriting quality:** Low confidence on heavily handwritten documents
- **Multi-column layouts:** May not preserve exact column order
- **Tables:** Preserved as text blocks, not structured tables
- **Medical symbols:** Best-effort preservation (depends on OCR capability)

---

## Deployment Architecture

### Local Deployment (Phase 1)

```
┌─────────────────────────────────────┐
│       Local Machine (User)          │
│                                     │
│  ┌───────────────────────────────┐  │
│  │   Python 3.10+ Environment    │  │
│  │                               │  │
│  │  ┌─────────────────────────┐  │  │
│  │  │  Streamlit App          │  │  │
│  │  │  (localhost:8501)       │  │  │
│  │  └─────────────────────────┘  │  │
│  │                               │  │
│  │  ┌─────────────────────────┐  │  │
│  │  │  Core Services          │  │  │
│  │  │  • OCR                  │  │  │
│  │  │  • Structuring          │  │  │
│  │  │  • Rendering            │  │  │
│  │  └─────────────────────────┘  │  │
│  │                               │  │
│  └───────────────────────────────┘  │
│                                     │
│  External API Calls:                │
│  └─→ Gemini API (HTTPS)             │
│                                     │
└─────────────────────────────────────┘
```

**No server infrastructure required.**

---

## Configuration

### Environment Variables

```bash
# .env file
GEMINI_API_KEY=your_api_key_here

# Optional
DEBUG=false
MAX_FILE_SIZE_MB=50
MAX_PAGE_COUNT=100
LOG_LEVEL=INFO
```

### Configuration File (Optional)

```yaml
# config.yaml
processing:
  max_file_size_mb: 50
  max_page_count: 100
  ocr_timeout_seconds: 30
  structuring_timeout_seconds: 120

output:
  include_debug_info: false
  default_format: pdf  # pdf | docx

logging:
  level: INFO
  include_phi: false  # Never log patient names
```

---

## File Structure

```
project/
├── src/
│   ├── services/
│   │   ├── ocr_service.py          # Gemini 3 Preview integration
│   │   ├── structuring_service.py  # Gemini 2.5 Flash integration
│   │   ├── rendering_service.py    # XML + PDF/DOCX generation
│   │   └── validation_service.py   # Schema validation
│   ├── models/
│   │   ├── canonical_schema.py     # Pydantic models
│   │   └── enums.py                # Enums (encounter types, etc.)
│   ├── utils/
│   │   ├── pdf_utils.py            # PDF handling
│   │   ├── retry_utils.py          # Exponential backoff
│   │   └── date_utils.py           # Date parsing/formatting
│   └── ui/
│       └── streamlit_app.py        # UI entry point
├── templates/
│   ├── ccd_template.xml.jinja2     # XML template
│   └── human_readable.html.jinja2 # HTML template
├── schemas/
│   └── canonical_v2.0.json         # JSON schema
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── docs/
│   ├── LLM_SYSTEM_PROMPT.md        # LLM instructions
│   ├── ARCHITECTURE.md             # This file
│   └── USER_GUIDE.md               # End-user documentation
├── requirements.txt
├── .env.example
├── README.md
└── main.py                         # CLI entry point (optional)
```

---

## Development Workflow

### Setup
```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

### Run Locally
```bash
# Start Streamlit UI
streamlit run src/ui/streamlit_app.py

# Or use CLI (if implemented)
python main.py --input sample.pdf --output results/
```

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src tests/

# Run specific test category
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/
```

---

## Monitoring & Observability

### Logging

**Structured logs:**
```json
{
  "timestamp": "2025-12-19T10:30:00Z",
  "level": "INFO",
  "component": "ocr_service",
  "message": "Processing page 3/15",
  "metadata": {
    "page_number": 3,
    "confidence": 0.92
  }
}
```

**Log levels:**
- `INFO`: Normal operations
- `WARN`: Recoverable issues (low confidence, missing data)
- `ERROR`: Processing failures

**PHI Handling:**
- Patient names/IDs NEVER logged (even in debug mode)
- Only log page numbers, confidence scores, error types

### Metrics (Future)

If adding metrics collection:
- Documents processed
- Processing time per page
- API call latency
- Error rates by type
- Confidence score distribution

---

## Summary

This architecture prioritizes:
- ✅ **Accuracy over inference** - Never guess
- ✅ **Traceability over automation** - Track all data sources
- ✅ **Determinism over creativity** - Same input = same output
- ✅ **Clarity over complexity** - Simple, maintainable design

It is designed for **safe, controlled medical document processing** with clear boundaries and explicit error handling.

---

**Questions or clarifications:** See `/docs/USER_GUIDE.md` or contact project owner.
