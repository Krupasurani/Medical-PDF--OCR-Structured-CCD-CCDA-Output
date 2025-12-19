# SYSTEM ARCHITECTURE — Medical PDF Processing Pipeline

## Overview

This system converts scanned medical PDFs into:
- **Canonical JSON** (source of truth)
- **CCD / CCDA-style XML** (structure-compatible, not certified HL7 conformance)
- **Human-readable medical documents** (PDF / DOCX)

The system is **local, single-user, and API-ready**.

---

## High-Level Flow

```
PDF
  ↓
Pre-validation
  ↓
Vision OCR
  ↓
Chunking
  ↓
Schema-enforced structuring
  ↓
Canonical JSON
  ↓
  ├── XML Renderer
  └── Human-readable Renderer
```

---

## Component Breakdown

### 1. PDF Ingestion

**Purpose:** Validate and prepare PDF for processing

**Checks:**
- File format validation
- Page count detection
- DPI & quality assessment
- Password detection
- File size limits (max 50MB)

**Rejects invalid or locked PDFs early.**

**Technology:**
- `pypdf` - PDF parsing
- `pdf2image` - Page image extraction
- `Pillow` - Image handling

---

### 2. Vision OCR Engine

**Purpose:** Extract text exactly as written (no interpretation)

**Process:**
- Page-by-page image processing
- Handwritten + printed text extraction
- Layout preservation
- Confidence scoring

**Output:**
```json
{
  "page_number": 1,
  "raw_text": "...",
  "confidence_score": 0.92,
  "layout_hints": {
    "has_tables": true,
    "has_handwriting": true
  }
}
```

**Rules:**
- No medical reasoning
- No interpretation
- Preserve all symbols and abbreviations

**Model:** Vision OCR engine (model-agnostic interface)

---

### 3. Chunking Engine

**Purpose:** Organize OCR text into logical sections

**Methods:**
- Visit detection (boundary identification)
- Date grouping (explicit dates only)
- Encounter separation

**Uses:**
- Rule-based logic (date patterns, section headers)
- LLM assistance for ambiguous boundaries

**Output:** Segmented text blocks with metadata

---

### 4. Structuring Engine

**Purpose:** Map OCR text to strict JSON schema

**Responsibilities:**
- Populate canonical JSON schema
- Deduplicate repeated entries (exact + fuzzy matching)
- Preserve all conflicts (never auto-resolve)
- Flag uncertainty

**Rules:**
- No hallucination permitted
- No invented dates or values
- No silent corrections

**Model:** Structuring/reasoning engine (model-agnostic interface)

---

### 5. Canonical JSON Layer

**Purpose:** Single source of truth for all outputs

**Characteristics:**
- Schema-enforced (Pydantic validation)
- All downstream outputs MUST render from this JSON
- No re-extraction allowed in rendering phase
- Version-controlled schema (currently v2.0)

**Schema sections:**
- `document_metadata` - Patient demographics
- `visits[]` - Clinical encounters
  - `medications[]`
  - `vital_signs{}`
  - `problem_list[]`
  - `results[]`
  - `assessment`
  - `plan[]`
- `data_quality` - Confidence scores, warnings

**File:** `schemas/canonical_v2.0.json`

---

### 6. XML Renderer

**Purpose:** Generate CCD/CCDA-style XML

**Method:**
- Template-based rendering (Jinja2)
- All data from canonical JSON
- No additional extraction logic

**Output Format:**
- CCD/CCDA-style structure (structure-compatible, not certified HL7 conformance)
- Human-readable XML
- UTF-8 encoding
- Schema validation (basic structure check)

**Technology:**
- `lxml` - XML processing
- `jinja2` - Templating

**Note:** This is "CCD/CCDA-style" - semantically similar structure, but NOT claiming full HL7 certification or conformance testing.

---

### 7. Human-Readable Renderer

**Purpose:** Generate clinical narrative document

**Method:**
- HTML template (Jinja2)
- Convert to PDF (reportlab) or DOCX (python-docx)
- Professional medical formatting

**Output:**
- Clear section headings
- Data quality warnings included
- `[UNCLEAR]` sections marked visually
- Source page references

**Technology:**
- `reportlab` - PDF generation
- `python-docx` - DOCX generation
- `jinja2` - Templating

---

## UI Layer (Phase 1)

**Framework:** Streamlit (local web interface)

**Characteristics:**
- Local execution only (localhost binding)
- Single-user (no authentication)
- No external exposure
- Session-based (no data persistence)

**User Flow:**
1. Upload PDF
2. Monitor processing (real-time progress)
3. Review warnings/confidence scores
4. Download outputs (JSON, XML, PDF, DOCX)

**Important:** This is a utility interface, NOT a security system. It provides:
- ✅ Local privacy (no external transmission)
- ✅ Temporary processing (no data retention)
- ❌ NOT multi-user authentication
- ❌ NOT access control
- ❌ NOT HIPAA-certified infrastructure

---

## Data Flow Diagram

```
┌─────────────────────────────────────────┐
│              User / Client               │
└─────────────────────────────────────────┘
                    ↓
          ┌──────────────────┐
          │  Streamlit UI    │
          │  (localhost)     │
          └──────────────────┘
                    ↓
       ┌────────────────────────┐
       │  PDF Validation        │
       │  (size, format, pages) │
       └────────────────────────┘
                    ↓
       ┌────────────────────────┐
       │  Vision OCR Engine     │
       │  (page-by-page)        │
       └────────────────────────┘
                    ↓
       ┌────────────────────────┐
       │  OCR Cache (memory)    │
       │  [page_1, page_2, ...] │
       └────────────────────────┘
                    ↓
       ┌────────────────────────┐
       │  Chunking Engine       │
       │  (visit detection)     │
       └────────────────────────┘
                    ↓
       ┌────────────────────────┐
       │  Structuring Engine    │
       │  (schema population)   │
       └────────────────────────┘
                    ↓
       ┌────────────────────────┐
       │  Canonical JSON        │
       │  (single source)       │
       └────────────────────────┘
                    ↓
          ┌─────────┴─────────┐
          ↓                   ↓
  ┌───────────────┐   ┌──────────────────┐
  │ XML Renderer  │   │ Human-Readable   │
  │ (template)    │   │ Renderer         │
  └───────────────┘   └──────────────────┘
          ↓                   ↓
  ┌───────────────┐   ┌──────────────────┐
  │   CCD XML     │   │   PDF / DOCX     │
  └───────────────┘   └──────────────────┘
                    ↓
          ┌──────────────────┐
          │  Download to User │
          └──────────────────┘
```

---

## Technology Stack

### Core Dependencies

**PDF Processing:**
- `pypdf==4.0.1`
- `pdf2image==1.17.0`
- `Pillow==10.2.0`

**AI/ML:**
- Vision OCR engine (model-agnostic client)
- Structuring/reasoning engine (model-agnostic client)

**Data Validation:**
- `pydantic==2.5.3` - Schema validation
- `jsonschema==4.20.0` - JSON schema validation

**Rendering:**
- `lxml==5.1.0` - XML processing
- `jinja2==3.1.3` - Templating
- `reportlab==4.0.9` - PDF generation
- `python-docx==1.1.0` - DOCX generation

**UI:**
- `streamlit==1.30.0`

**Utilities:**
- `python-dateutil==2.8.2` - Date parsing
- `python-dotenv==1.0.1` - Environment variables
- `tenacity==8.2.3` - Retry logic

**Python Version:** 3.10+ (recommended 3.11)

---

## Security & Privacy

### Data Handling
- ✅ **Local processing only** (no cloud storage)
- ✅ **In-memory processing** (files not persisted)
- ✅ **Temporary file cleanup** (automatic)
- ✅ **No logging of PHI** (configurable)
- ✅ **No data reuse** (each session isolated)
- ✅ **No external APIs exposed**

### Deployment
- ✅ **Localhost binding only** (`127.0.0.1`)
- ✅ **No network exposure**
- ✅ **No authentication** (single-user utility)

### Important Notes
- This is a **local utility**, not a security-hardened production system
- HIPAA-aligned practices are followed (minimum necessary, secure disposal)
- **NOT certified as HIPAA-compliant infrastructure**
- Consult legal/compliance before use in regulated environments

---

## API Readiness

Internal interfaces are modular and stateless.

**Current State (Phase 1):**
- Core services are callable Python functions
- No REST endpoints exposed
- No external API surface

**Future State (Phase 2):**
- REST API wrapping (FastAPI)
- Authentication (if multi-user)
- Rate limiting
- Async processing (job queue)

**Example future endpoints:**
```
POST /api/v1/process
  - Upload PDF
  - Response: Job ID

GET /api/v1/jobs/{job_id}
  - Check status
  - Response: Status + results

GET /api/v1/jobs/{job_id}/outputs/{type}
  - Download JSON/XML/PDF/DOCX
```

**No changes to core logic required** - only add API wrapper.

---

## Error Handling Philosophy

### Principles
- **Fail loudly** - No silent failures
- **Log clearly** - Structured logging with context
- **Preserve partial results** - Return what was successfully extracted
- **Never continue silently** - Alert user to issues

### Error Categories

| Error Type | Handling | User Message |
|------------|----------|--------------|
| Invalid PDF | Reject upload | "PDF file is corrupted or invalid" |
| File too large | Reject upload | "File exceeds 50MB limit" |
| OCR failure | Retry 3x, then partial results | "OCR failed for page 3, continuing with remaining pages" |
| API timeout | Retry with exponential backoff | "Processing delayed, retrying..." |
| Schema validation | Accept with warnings | "Output may be incomplete, see warnings" |
| No text detected | Return empty JSON | "No text detected in document" |

### Retry Logic
```python
MAX_RETRIES = 3
BACKOFF_MULTIPLIER = 2
INITIAL_DELAY = 1  # second

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

**Note:** Estimates based on reasonable quality scans (200+ DPI) and normal API latency.

### Resource Usage

**Memory:**
- Peak: ~2GB per document
- Streaming for large files

**Disk:**
- Temporary storage: ~2x file size
- Auto-cleanup after processing

---

## File Structure

```
project/
├── src/
│   ├── services/
│   │   ├── ocr_service.py          # Vision OCR integration
│   │   ├── structuring_service.py  # Structuring engine integration
│   │   ├── rendering_service.py    # XML + PDF/DOCX generation
│   │   └── validation_service.py   # Schema validation
│   ├── models/
│   │   ├── canonical_schema.py     # Pydantic models
│   │   └── enums.py                # Enums (encounter types, etc.)
│   ├── utils/
│   │   ├── pdf_utils.py            # PDF handling
│   │   ├── retry_utils.py          # Exponential backoff
│   │   └── date_utils.py           # Date parsing
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
- Golden datasets (5 representative samples)

**Test Framework:** pytest

---

## Limitations & Constraints

### Current Scope (Phase 1)
- ✅ Local deployment only
- ✅ Single-user operation
- ✅ No authentication
- ✅ No persistent storage
- ✅ CCD/CCDA-style XML (structure-compatible, not certified)

### Explicitly Out of Scope
- ❌ Cloud deployment
- ❌ Multi-user support
- ❌ Public API exposure
- ❌ Clinical decision support
- ❌ Medical code validation (ICD-10, CPT)
- ❌ EHR system integration
- ❌ Real-time processing
- ❌ Full HL7 FHIR R4 compliance

### Known Edge Cases
- **Handwriting quality:** Low confidence on heavily handwritten documents
- **Multi-column layouts:** May not preserve exact column order
- **Tables:** Preserved as text blocks, not structured tables
- **Medical symbols:** Best-effort preservation

---

## Configuration

### Environment Variables

```bash
# .env file
VISION_OCR_API_KEY=your_api_key_here
STRUCTURING_API_KEY=your_api_key_here

# Optional
DEBUG=false
MAX_FILE_SIZE_MB=50
MAX_PAGE_COUNT=100
LOG_LEVEL=INFO
LOG_PHI=false  # Never log patient names
```

---

## Summary

This architecture prioritizes:
- ✅ **Accuracy over inference** - Never guess
- ✅ **Traceability over automation** - Track all data sources
- ✅ **Determinism over creativity** - Same input = same output
- ✅ **Clarity over complexity** - Simple, maintainable design
- ✅ **Fail loudly over silent errors** - Always surface issues

It is designed for **safe, controlled medical document processing** with clear boundaries and explicit error handling.

---

**Questions or clarifications:** See documentation in `/docs/` or contact project owner.
