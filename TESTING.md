# Testing Guide - Milestone 1

## Setup

### 1. Create Virtual Environment

```bash
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure API Key

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your Gemini API key
# Get API key from: https://ai.google.dev/
nano .env  # or use your preferred editor
```

Example `.env` file:
```bash
GEMINI_API_KEY=your_actual_api_key_here
DEBUG=true
MAX_FILE_SIZE_MB=50
MAX_PAGE_COUNT=100
LOG_LEVEL=INFO
```

---

## Running Unit Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src tests/

# Run specific test file
pytest tests/unit/test_models.py

# Run with verbose output
pytest -v

# Run and show print statements
pytest -s
```

---

## Testing the Full Pipeline

### Option 1: Using Main Script

```bash
# Process a medical PDF
python main.py --input "C:\Users\a\Downloads\notes_fnl (3).pdf" --output output/
#C:\Users\a\Downloads\notes_fnl (3).pdf
# With debug mode (saves intermediate results)
python main.py --input sample.pdf --output output/ --debug
```

### Option 2: Using Python Directly

```python
from src.services.pdf_service import PDFService
from src.services.ocr_service import OCRService
from src.services.chunking_service import ChunkingService
from src.services.structuring_service import StructuringService

# Step 1: PDF Processing
pdf_service = PDFService()
pdf_data = pdf_service.process_pdf("sample.pdf")

# Step 2: OCR
ocr_service = OCRService()
ocr_results = ocr_service.process_pages(pdf_data["images"])

# Step 3: Chunking
chunking_service = ChunkingService()
chunks = chunking_service.chunk_pages(ocr_results)

# Step 4: Structuring
structuring_service = StructuringService()
document = structuring_service.structure_document(chunks, ocr_results)

# Save output
with open("output/canonical.json", "w") as f:
    f.write(document.model_dump_json())
```

---

## Creating Test PDFs

### Option 1: Use Existing Medical Records
- Anonymize real medical records (remove all PHI)
- Use publicly available sample medical records

### Option 2: Create Synthetic Medical PDFs

You can create test PDFs with tools like:
- Microsoft Word → Save as PDF
- Google Docs → Download as PDF
- Online PDF generators

**Example Medical Note Template:**

```
MEDICAL RECORD

Patient: Test Patient
DOB: 01/01/1980
Visit Date: 12/15/2025

CHIEF COMPLAINT:
Headache x 3 days

HISTORY OF PRESENT ILLNESS:
Patient presents with frontal headache for 3 days.
Pain is throbbing, 7/10 severity.

PAST MEDICAL HISTORY:
- Hypertension
- Type 2 Diabetes Mellitus

MEDICATIONS:
- Lisinopril 10mg daily
- Metformin 500mg BID

ALLERGIES:
Penicillin

VITAL SIGNS:
BP: 135/85 mmHg
HR: 78 bpm
Temp: 98.6°F

PHYSICAL EXAM:
Alert and oriented x3
HEENT: PERRLA, no focal deficits

ASSESSMENT:
Tension headache

PLAN:
1. Ibuprofen 400mg PRN
2. Follow up in 1 week if symptoms persist
3. Consider imaging if no improvement
```

---

## Expected Output

### Canonical JSON Structure

```json
{
  "schema_version": "2.0",
  "document_metadata": {
    "patient_name": "Test Patient",
    "dob": "1980-01-01",
    "document_date": "2025-12-15"
  },
  "visits": [
    {
      "visit_id": "visit_001",
      "visit_date": "2025-12-15",
      "reason_for_visit": "Headache x 3 days",
      "history_of_present_illness": "Patient presents with frontal headache...",
      "medications": [
        {
          "name": "Lisinopril",
          "dose": "10mg",
          "frequency": "daily",
          "source_page": 1
        }
      ],
      "vital_signs": {
        "blood_pressure": {
          "systolic": 135,
          "diastolic": 85,
          "unit": "mmHg",
          "source_page": 1
        }
      },
      "assessment": "Tension headache",
      "plan": [
        {
          "action": "Ibuprofen 400mg PRN",
          "source_page": 1
        }
      ],
      "raw_source_pages": [1]
    }
  ],
  "data_quality": {
    "confidence_score": 0.95,
    "unclear_sections": []
  }
}
```

---

## Troubleshooting

### API Key Errors

```bash
# Error: API key not found
# Solution: Check .env file exists and contains GEMINI_API_KEY

# Verify .env is loaded
python -c "from src.utils.config import get_config; print(get_config().gemini_api_key[:10])"
```

### PDF Processing Errors

```bash
# Error: PDF is password-protected
# Solution: Remove password or use unlocked PDF

# Error: File size exceeds limit
# Solution: Reduce file size or increase MAX_FILE_SIZE_MB in .env
```

### OCR/Gemini API Errors

```bash
# Error: Rate limit exceeded
# Solution: Wait and retry, or check API quota

# Error: Invalid model name
# Solution: Check model name in ocr_service.py and structuring_service.py
```

---

## Performance Benchmarks (Expected)

| Document Size | Processing Time | Memory Usage |
|---------------|-----------------|--------------|
| 1-5 pages     | < 60s           | < 1GB        |
| 6-20 pages    | < 3 min         | < 2GB        |

**Note:** Times depend on PDF quality, handwriting complexity, and API latency.

---

## Next Steps (Milestone 2)

After successful Milestone 1 testing:
1. ✅ XML renderer (CCD/CCDA-style)
2. ✅ Human-readable renderer (PDF/DOCX)
3. ✅ Streamlit UI
4. ✅ End-to-end integration tests
