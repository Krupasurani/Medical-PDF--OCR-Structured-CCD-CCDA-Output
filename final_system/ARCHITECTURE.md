# System Architecture

Medical PDF → CCD/CCDA Converter system architecture and design overview.

## Overview

The system is a document processing pipeline that transforms medical PDF documents into structured, standards-compliant outputs through a multi-stage process.

## High-Level Architecture

\`\`\`
PDF Input → OCR → Structuring → Generation → Multiple Outputs
\`\`\`

### Processing Pipeline

1. **PDF Processing**
   - Input validation
   - Page extraction
   - Image conversion (300 DPI)

2. **OCR (Optical Character Recognition)**
   - Text extraction from images
   - Handwriting recognition
   - Layout analysis

3. **Structuring**
   - Medical data extraction
   - Entity recognition (medications, diagnoses, lab results)
   - Structured data organization

4. **Generation**
   - CCD/CCDA XML creation
   - Professional PDF reports
   - DOCX documents
   - JSON structured data

## System Components

### Web Interface

- **Technology**: Streamlit web framework
- **Features**:
  - File upload (PDF, max 200MB)
  - Progress tracking
  - Real-time status updates
  - Multi-format downloads (ZIP, individual files)

### PDF Service

- **Input**: Medical PDF documents
- **Processing**:
  - PDF validation
  - Page-by-page image extraction
  - Quality checks
- **Output**: Image data for OCR

### OCR Service

- **Input**: Page images
- **Processing**:
  - Advanced vision-based text recognition
  - Handwriting and printed text extraction
  - Layout preservation
- **Output**: Raw text with confidence scores

### Structuring Service

- **Input**: Raw OCR text
- **Processing**:
  - Medical entity extraction
  - Data validation
  - Canonical format conversion
- **Output**: Structured JSON data

### Rendering Services

#### XML Renderer
- **Input**: Structured data
- **Output**: HL7 CCD/CCDA R2.1 XML
- **Compliance**:
  - Practice Fusion CDA R2.1 templates
  - Proper namespace declarations
  - Required sections and codes

#### PDF Renderer
- **Input**: Structured data
- **Output**: Professional clinical summary
- **Features**:
  - Professional header
  - Organized sections
  - Lab results tables
  - Treatment plans with checkboxes

#### DOCX Renderer
- **Input**: Structured data
- **Output**: Editable Word document
- **Features**:
  - Formatted sections
  - Tables for structured data
  - Professional styling

## Data Flow

\`\`\`
┌─────────────┐
│   PDF File  │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│  PDF Processing │ → Page Images
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│   OCR Service   │ → Raw Text
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│   Structuring   │ → Structured JSON
└─────────┬───────┘
          │
          ├──────────────┬──────────────┬──────────────┐
          │              │              │              │
          ▼              ▼              ▼              ▼
    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
    │   XML   │    │   PDF   │    │  DOCX   │    │  JSON   │
    │ Renderer│    │ Renderer│    │ Renderer│    │  Export │
    └─────────┘    └─────────┘    └─────────┘    └─────────┘
          │              │              │              │
          ▼              ▼              ▼              ▼
    CCD/CCDA XML    Clinical PDF    Word Doc    Structured Data
\`\`\`

## Output Specifications

### CCD/CCDA XML

**Standard**: HL7 CCD R2.1

**Required Sections**:
- Header (patient demographics, document metadata)
- Medications
- Allergies
- Problem List
- Procedures
- Results (lab values)
- Vital Signs
- Plan of Care

**Compliance**: 
- Proper OID identifiers
- LOINC/SNOMED codes where applicable
- Template IDs per CDA R2.1

### Clinical PDF

**Format**: Professional consultation note

**Sections**:
- Header (patient info, visit date)
- Laboratory Results (grouped by category)
- Physical Examination
- Clinical Assessment (with reasoning)
- Treatment Plan (organized with checkboxes)

### DOCX Document

**Format**: Editable Word document

**Content**:
- All structured sections
- Tables for lab results
- Formatted lists
- Professional styling

### JSON Data

**Format**: Canonical schema

**Structure**:
- Document metadata
- Visit array
- Per-visit data:
  - Demographics
  - Medications
  - Diagnoses
  - Lab results
  - Vital signs
  - Plan items

## Deployment Architecture

### Standalone Application

\`\`\`
┌─────────────────────────────────────┐
│   Local Machine                     │
│                                     │
│  ┌──────────────┐                  │
│  │  Streamlit   │                  │
│  │  Web Server  │                  │
│  │  (Port 8501) │                  │
│  └──────┬───────┘                  │
│         │                           │
│  ┌──────▼───────┐                  │
│  │  Processing  │                  │
│  │   Pipeline   │                  │
│  └──────┬───────┘                  │
│         │                           │
│  ┌──────▼───────┐                  │
│  │    Local     │                  │
│  │   Storage    │                  │
│  │  (outputs/)  │                  │
│  └──────────────┘                  │
└─────────────────────────────────────┘
         │
         │ HTTPS
         ▼
┌─────────────────┐
│   Gemini API    │
│ (Cloud Service) │
└─────────────────┘
\`\`\`

## Technology Stack

### Core Technologies

- **Python 3.9+**: Primary language
- **Streamlit**: Web UI framework
- **Google Gemini API**: AI/ML services

### Key Libraries

- **pypdf**: PDF processing
- **Pillow**: Image manipulation
- **python-docx**: Word document generation
- **reportlab**: PDF generation
- **pydantic**: Data validation

### External Services

- **Google Gemini**: Vision and language models
- Required for OCR and structuring

## Security & Privacy

### Data Flow

- PDF uploaded via browser → Local processing
- Images sent to Gemini API (HTTPS)
- Structured data processed locally
- Outputs saved to local disk only

### API Security

- API key stored in `.env` file (never committed to version control)
- HTTPS encryption for all API calls
- No data retention by API service (per Google's terms)

### Local Security

- All outputs saved locally
- No database or persistent storage
- No network exposure beyond localhost

## Scalability Considerations

### Current Limitations

- Single-user standalone application
- Sequential processing (one document at a time)
- API rate limits apply

### Performance

- **Processing Speed**: 10-30 seconds per page
- **Throughput**: Depends on API quota
- **Concurrency**: Single document at a time

### Future Enhancements

- Batch processing support
- Multi-user deployment
- Database integration
- Cloud deployment options

## Configuration

### Environment Variables

\`\`\`env
GEMINI_API_KEY=<api-key>      # Required
OCR_MODEL_NAME=<model>         # Optional
STRUCTURING_MODEL_NAME=<model> # Optional
PDF_DPI=300                    # Optional
\`\`\`

### Customization Points

- Model selection (OCR and structuring)
- PDF processing quality (DPI)
- Output directory structure
- UI branding and styling

## Error Handling

### Graceful Degradation

- Failed pages marked with [UNCLEAR] markers
- Partial processing continues
- Error details logged
- User-friendly error messages

### Validation

- Input validation (PDF format, size)
- Output validation (schema compliance)
- API response validation

## Compliance

### Standards

- HL7 CCD/CCDA R2.1
- Practice Fusion templates
- LOINC for lab results
- SNOMED for conditions (where applicable)

### Data Quality

- Confidence scoring for OCR
- Data validation checks
- Manual review flags for low-confidence extractions

## Support & Maintenance

### Logging

- Structured logging to console
- Per-step progress tracking
- Error details for troubleshooting

### Monitoring

- Real-time progress updates in UI
- Processing metrics display
- Success/failure indicators

---

For detailed setup instructions, see [SETUP.md](SETUP.md).

For usage information, see [README.md](README.md).
