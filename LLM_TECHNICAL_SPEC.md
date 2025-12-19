# LLM_TECHNICAL_SPEC.md

**Project:** Medical PDF → OCR → Structured CCD / CCDA Output
**Client:** Internal (Upwork Contract)
**Owner:** Krupali Surani
**Phase:** Production-Ready, API-Ready (UI Local Only)
**Document Version:** 2.0 (Production-Grade)
**Last Updated:** 2025-12-19

---

## 1. Product Overview (PRD-style)

### Objective
Build a **local, secure, single-user Python system** that converts scanned medical PDFs into:
1. **Canonical JSON** (schema-enforced, single source of truth)
2. **CCD / CCDA-style XML** (clinical interoperability standard)
3. **Human-readable document** (HTML → PDF / DOCX)

The system must:
- ✅ Preserve original handwritten meaning with **zero hallucination**
- ✅ Support medical continuity-of-care workflows
- ✅ Provide deterministic, repeatable results
- ✅ Handle edge cases gracefully with clear error reporting
- ✅ Meet production-grade reliability standards

---

## 2. Scope Definition

### IN SCOPE (Phase 1 – Contracted)
- ✅ Vision-based OCR for **handwritten + printed + mixed** PDFs
- ✅ Intelligent visit/date/encounter chunking
- ✅ Schema-enforced medical structuring with validation
- ✅ Deduplication & merge logic (fuzzy + exact matching)
- ✅ Deterministic rendering: JSON → XML, JSON → Human-readable
- ✅ Local Streamlit UI (upload → process → download)
- ✅ API-ready internal architecture
- ✅ Comprehensive error handling and logging
- ✅ OCR confidence scoring and quality metrics
- ✅ Data validation and integrity checks

### OUT OF SCOPE (Explicitly)
- ❌ Multi-user authentication
- ❌ Cloud deployment
- ❌ External API exposure
- ❌ Model fine-tuning
- ❌ Billing / usage tracking
- ❌ Real-time processing
- ❌ FHIR R4 full compliance (limited to CCD/CCDA subset)

---

## 3. Model Strategy (CRITICAL – DO NOT DEVIATE)

### Model 1 — **Gemini 3 Preview** (Vision OCR Layer)

**Purpose:** Vision OCR ONLY – Maximum fidelity text extraction

**Responsibilities:**
- Read scanned PDFs page-by-page with high-resolution processing
- Extract raw visible text **exactly as written**
- Preserve:
  - Line breaks and spatial layout
  - Medical abbreviations (do NOT expand)
  - Symbols: `↑ ↓ → ± ≥ ≤ ° % / -`
  - Handwritten notation styles
  - Tables and structured data (preserve structure markers)
- Mark uncertainty as `[UNCLEAR: <partial_text>]`
- **NO medical reasoning**
- **NO autocorrection**
- **NO summarization**
- **NO interpretation**

**Output Schema:**
```json
{
  "page_number": 1,
  "raw_text": "...",
  "confidence_score": 0.95,
  "layout_hints": {
    "has_tables": true,
    "has_handwriting": true,
    "has_stamps": false,
    "rotation_detected": 0
  },
  "processing_metadata": {
    "ocr_engine_version": "gemini-3-preview",
    "timestamp": "2025-12-19T10:30:00Z",
    "processing_time_ms": 1234
  }
}
```

**Edge Cases Handled:**
- Rotated pages (auto-detect 90°, 180°, 270°)
- Low contrast / faded scans
- Mixed handwriting + printed text
- Multi-column layouts
- Overlapping text (stamps, signatures)
- Non-English characters in medical notes
- Partial obscuration (redaction marks, highlights)

---

### Model 2 — **Gemini 2.5 Flash** (Medical Intelligence Layer)

**Purpose:** Medical structuring, reasoning, and semantic extraction

**Responsibilities:**
- Chunk OCR text by:
  - **Visit** (distinct clinical encounters)
  - **Encounter type** (inpatient, outpatient, ER, consultation)
  - **Date** (inferred from explicit dates ONLY, not invented)
- Map content into **strict JSON schema** with validation
- Perform:
  - Section classification (SOAP notes, discharge summaries, lab reports)
  - Deduplication (exact + fuzzy matching with 85% threshold)
  - Merge repeated findings (preserve all values with source tracking)
  - Relationship extraction (symptoms → diagnoses → treatments)
- **NO hallucination**
- **NO adding medical facts not present in source**
- **NO inventing dates, values, or interpretations**
- Flag ambiguities for human review

**Output:** Canonical JSON (see Section 5)

**Edge Cases Handled:**
- Conflicting dates within document
- Missing patient identifiers
- Incomplete visit records
- Duplicate lab values with different units
- Ambiguous medical abbreviations (context-aware resolution)
- Illegible critical fields (flag for manual review)
- Multi-visit documents (chronological ordering)

---

## 4. End-to-End Pipeline (Authoritative)

```
┌─────────────────────────────────────────────────────────────┐
│                      INPUT: Medical PDF                      │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│  Pre-Processing & Validation                                 │
│  • PDF integrity check                                       │
│  • Password detection                                        │
│  • Page count validation                                     │
│  • DPI quality check (minimum 200 DPI recommended)          │
│  • File size limits (max 50MB per file)                     │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│  Gemini 3 Preview (Vision OCR)                              │
│  • Page-by-page extraction                                   │
│  • Confidence scoring                                        │
│  • Layout detection                                          │
│  • Quality metrics                                           │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│  Post-OCR Validation                                         │
│  • Confidence threshold check (min 70% per page)            │
│  • Character encoding validation                             │
│  • Layout consistency check                                  │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│  Chunking Engine (Rule-Based + LLM-Assisted)                │
│  • Visit boundary detection                                  │
│  • Date extraction and normalization                         │
│  • Section identification                                    │
│  • Context window management                                 │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│  Gemini 2.5 Flash (Schema-Enforced Structuring)            │
│  • Medical entity extraction                                 │
│  • Relationship mapping                                      │
│  • Deduplication logic                                       │
│  • Schema validation                                         │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│  Data Validation & Quality Checks                           │
│  • Schema conformance                                        │
│  • Required field validation                                 │
│  • Cross-field consistency                                   │
│  • Medical code validation (if present)                     │
│  • Date range validation                                     │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│                    CANONICAL JSON                            │
│              (Single Source of Truth)                        │
└─────────────────────────────────────────────────────────────┘
                             ↓
                    ┌────────┴────────┐
                    ↓                 ↓
┌──────────────────────────┐  ┌─────────────────────────┐
│  XML Renderer            │  │  Human-Readable         │
│  (CCD/CCDA-style)        │  │  Renderer               │
│  • Template-based        │  │  (HTML → PDF/DOCX)      │
│  • Standards-compliant   │  │  • Clinical narrative   │
│  • Validation            │  │  • Professional layout  │
└──────────────────────────┘  └─────────────────────────┘
```

---

## 5. Canonical JSON Schema (SOURCE OF TRUTH)

⚠️ **CRITICAL:** XML and human-readable files MUST be rendered ONLY from this JSON
⚠️ **NO LOGIC DUPLICATION ALLOWED**

### Schema Version: 2.0

```json
{
  "schema_version": "2.0",
  "document_metadata": {
    "patient_name": null,
    "patient_id": null,
    "dob": null,
    "sex": null,
    "document_date": null,
    "document_type": "mixed|discharge_summary|lab_report|consultation_note",
    "author": null,
    "organization": null,
    "processing_metadata": {
      "processed_at": "2025-12-19T10:30:00Z",
      "processing_duration_ms": 5432,
      "ocr_confidence_avg": 0.92,
      "page_count": 5,
      "warnings": [],
      "errors": []
    }
  },
  "visits": [
    {
      "visit_id": "visit_001",
      "visit_date": "2025-01-15",
      "encounter_type": "outpatient|inpatient|emergency|telehealth",
      "reason_for_visit": "",
      "history_of_present_illness": "",
      "past_medical_history": [],
      "medications": [
        {
          "name": "",
          "dose": "",
          "frequency": "",
          "route": "",
          "start_date": null,
          "end_date": null,
          "source_page": 1
        }
      ],
      "allergies": [],
      "vital_signs": {
        "temperature": {"value": null, "unit": "F|C", "source_page": 1},
        "blood_pressure": {"systolic": null, "diastolic": null, "unit": "mmHg", "source_page": 1},
        "heart_rate": {"value": null, "unit": "bpm", "source_page": 1},
        "respiratory_rate": {"value": null, "unit": "breaths/min", "source_page": 1},
        "oxygen_saturation": {"value": null, "unit": "%", "source_page": 1},
        "weight": {"value": null, "unit": "kg|lbs", "source_page": 1},
        "height": {"value": null, "unit": "cm|in", "source_page": 1},
        "bmi": {"value": null, "calculated": true}
      },
      "problem_list": [
        {
          "problem": "",
          "icd10_code": null,
          "status": "active|resolved|chronic",
          "onset_date": null,
          "source_page": 1
        }
      ],
      "results": [
        {
          "test_name": "",
          "value": "",
          "unit": "",
          "reference_range": "",
          "abnormal_flag": "normal|high|low|critical",
          "test_date": null,
          "source_page": 1
        }
      ],
      "assessment": "",
      "plan": [
        {
          "action": "",
          "category": "medication|procedure|referral|lifestyle|followup",
          "source_page": 1
        }
      ],
      "raw_source_pages": [1, 2],
      "extraction_confidence": 0.95,
      "manual_review_required": false,
      "review_reasons": []
    }
  ],
  "data_quality": {
    "completeness_score": 0.87,
    "confidence_score": 0.92,
    "unclear_sections": [
      {
        "section": "medications",
        "page": 3,
        "reason": "Handwriting illegible",
        "original_text": "[UNCLEAR: partial text]"
      }
    ],
    "missing_critical_fields": []
  }
}
```

### Field Validation Rules

| Field | Required | Validation | Error Handling |
|-------|----------|------------|----------------|
| `patient_name` | No* | String, 2-100 chars | Flag if missing |
| `dob` | No* | ISO 8601 date, reasonable range (1900-present) | Flag if missing |
| `visit_date` | Yes | ISO 8601, not future date | Reject visit if missing |
| `medications.dose` | No | Must include unit if present | Warn if unit missing |
| `vital_signs.*` | No | Range validation (e.g., BP 40-300 mmHg) | Warn if out of range |
| `icd10_code` | No | Format validation (A00.0 - Z99.9) | Warn if invalid |

*Critical for clinical use but may be missing from incomplete documents

---

## 6. XML Output Requirements (CCD/CCDA-Style)

### Standards Compliance
- **Base Standard:** HL7 CCD (Continuity of Care Document)
- **Schema Validation:** MUST validate against CCD XSD
- **Encoding:** UTF-8
- **Format:** Human-readable with proper indentation

### Required CCD Sections
```xml
<?xml version="1.0" encoding="UTF-8"?>
<ClinicalDocument xmlns="urn:hl7-org:v3">
  <realmCode code="US"/>
  <typeId root="2.16.840.1.113883.1.3" extension="POCD_HD000040"/>

  <!-- Patient Demographics -->
  <recordTarget>
    <patientRole>
      <id root="2.16.840.1.113883.3.1" extension="{patient_id}"/>
      <patient>
        <name>
          <given>{first_name}</given>
          <family>{last_name}</family>
        </name>
        <birthTime value="{YYYYMMDD}"/>
        <administrativeGenderCode code="{M|F|U}" codeSystem="2.16.840.1.113883.5.1"/>
      </patient>
    </patientRole>
  </recordTarget>

  <!-- Structured Body -->
  <component>
    <structuredBody>
      <!-- Reason for Visit -->
      <component>
        <section>
          <code code="29299-5" codeSystem="2.16.840.1.113883.6.1" displayName="Reason for visit"/>
          <title>Reason for Visit</title>
          <text>{reason_for_visit}</text>
        </section>
      </component>

      <!-- History of Present Illness -->
      <component>
        <section>
          <code code="10164-2" codeSystem="2.16.840.1.113883.6.1" displayName="History of Present Illness"/>
          <title>History of Present Illness</title>
          <text>{history_of_present_illness}</text>
        </section>
      </component>

      <!-- Problem List -->
      <component>
        <section>
          <code code="11450-4" codeSystem="2.16.840.1.113883.6.1" displayName="Problem List"/>
          <title>Problem List</title>
          <text>
            <list>
              <!-- Repeat for each problem -->
              <item>{problem_description}</item>
            </list>
          </text>
          <entry>
            <act classCode="ACT" moodCode="EVN">
              <templateId root="2.16.840.1.113883.10.20.22.4.3"/>
              <!-- Structured problem entries -->
            </act>
          </entry>
        </section>
      </component>

      <!-- Results -->
      <component>
        <section>
          <code code="30954-2" codeSystem="2.16.840.1.113883.6.1" displayName="Relevant diagnostic tests/laboratory data"/>
          <title>Results</title>
          <text>
            <table>
              <thead>
                <tr>
                  <th>Test</th>
                  <th>Value</th>
                  <th>Unit</th>
                  <th>Reference Range</th>
                  <th>Flag</th>
                </tr>
              </thead>
              <tbody>
                <!-- Repeat for each result -->
                <tr>
                  <td>{test_name}</td>
                  <td>{value}</td>
                  <td>{unit}</td>
                  <td>{reference_range}</td>
                  <td>{abnormal_flag}</td>
                </tr>
              </tbody>
            </table>
          </text>
        </section>
      </component>

      <!-- Assessment -->
      <component>
        <section>
          <code code="51848-0" codeSystem="2.16.840.1.113883.6.1" displayName="Assessment"/>
          <title>Assessment</title>
          <text>{assessment}</text>
        </section>
      </component>

      <!-- Plan -->
      <component>
        <section>
          <code code="18776-5" codeSystem="2.16.840.1.113883.6.1" displayName="Plan of Care"/>
          <title>Plan</title>
          <text>
            <list>
              <!-- Repeat for each plan item -->
              <item>{plan_action}</item>
            </list>
          </text>
        </section>
      </component>
    </structuredBody>
  </component>
</ClinicalDocument>
```

### XML Generation Rules
1. **Empty Section Handling:**
   - If section is empty → include section with `<text>No information available</text>`
   - NEVER omit required CCD sections
   - NEVER invent data to fill sections

2. **Data Mapping:**
   - All content MUST come from canonical JSON
   - Preserve traceability (comments with source pages)
   - Escape special characters properly

3. **Validation:**
   - Validate against CCD XSD before output
   - Log validation errors
   - Provide fallback to "best effort" XML if validation fails (with warnings)

---

## 7. Human-Readable Output

### Format Options
1. **PDF** (primary)
   - Professional medical document styling
   - Consistent typography
   - Page headers with patient demographics
   - Section headings with visual hierarchy

2. **DOCX** (secondary)
   - Editable format for clinical review
   - Consistent with PDF styling
   - Template-based generation

### Document Structure
```
┌─────────────────────────────────────────────┐
│         MEDICAL RECORD SUMMARY              │
│                                             │
│  Patient: {name}                            │
│  DOB: {dob}                                 │
│  Visit Date: {visit_date}                   │
│                                             │
│  Document Generated: {timestamp}            │
│  Source: OCR-processed medical record       │
└─────────────────────────────────────────────┘

REASON FOR VISIT
────────────────
{reason_for_visit}

HISTORY OF PRESENT ILLNESS
──────────────────────────
{history_of_present_illness}

PAST MEDICAL HISTORY
────────────────────
• {history_item_1}
• {history_item_2}

MEDICATIONS
───────────
┌──────────────────┬────────┬───────────┬───────┐
│ Medication       │ Dose   │ Frequency │ Route │
├──────────────────┼────────┼───────────┼───────┤
│ {med_name}       │ {dose} │ {freq}    │{route}│
└──────────────────┴────────┴───────────┴───────┘

[... additional sections ...]

DATA QUALITY NOTES
──────────────────
⚠ Sections with reduced confidence:
  • {section}: {reason}

Source Pages: {page_list}
```

### Styling Requirements
- **Font:** Professional sans-serif (Arial, Helvetica) for body, serif for headings
- **Colors:** Black text on white, minimal use of color (red for warnings only)
- **Layout:** Consistent margins (1" all sides), clear section breaks
- **Tables:** Bordered, alternating row colors for readability
- **Warnings:** Clearly marked with ⚠ symbol

---

## 8. Deduplication & Merge Rules

### Exact Match Deduplication
**Criteria:** Identical text (case-insensitive, whitespace-normalized)
```python
# Example: Duplicate problem entries
"Hypertension" == "hypertension" == "  Hypertension  "
→ Keep first occurrence, track all source pages
```

### Fuzzy Match Deduplication
**Algorithm:** Levenshtein distance with 85% similarity threshold
```python
# Example: Lab values
"Glucose: 110 mg/dL" ≈ "Blood Glucose 110 mg/dl" (90% similar)
→ Merge with both source pages, prefer more complete version
```

### Merge Strategies by Data Type

#### 1. Lab Results
```json
// Input: Same test, different pages
Page 3: "Glucose: 110 mg/dL (H) [70-100]"
Page 5: "Glucose 110"

// Output: Merged entry
{
  "test_name": "Glucose",
  "value": "110",
  "unit": "mg/dL",
  "reference_range": "70-100",
  "abnormal_flag": "high",
  "source_pages": [3, 5],
  "merge_confidence": 0.95
}
```

#### 2. Diagnoses/Problems
```json
// Input: Similar diagnoses
Page 1: "Type 2 Diabetes Mellitus"
Page 4: "DM Type 2"

// Output: Merged (preserve most complete)
{
  "problem": "Type 2 Diabetes Mellitus",
  "alternative_representations": ["DM Type 2"],
  "source_pages": [1, 4],
  "icd10_code": "E11.9"  // Only if explicitly stated
}
```

#### 3. Medications
```json
// Input: Same medication, different details
Page 2: "Metformin 500mg"
Page 6: "Metformin 500mg BID PO"

// Output: Merged (prefer more complete)
{
  "name": "Metformin",
  "dose": "500mg",
  "frequency": "BID",
  "route": "PO",
  "source_pages": [2, 6]
}
```

### Conflict Resolution Rules
1. **Date conflicts:** Flag for manual review, use earliest date if both plausible
2. **Value conflicts:** Report both values with source pages
3. **Unit conflicts:** Attempt conversion, flag if incompatible
4. **Contradictory information:** NEVER auto-resolve, always flag for review

---

## 9. Edge Cases & Error Handling

### PDF Input Edge Cases

| Edge Case | Detection | Handling | User Feedback |
|-----------|-----------|----------|---------------|
| **Password-protected PDF** | Pre-processing check | Reject with clear error | "PDF is password-protected. Please provide unlocked version." |
| **Corrupted/malformed PDF** | pypdf validation | Attempt recovery, reject if fails | "PDF file appears corrupted. Bytes {range} unreadable." |
| **Scanned at angle** | Gemini layout detection | Auto-rotate if <15°, warn if >15° | "Document rotation detected: {degrees}°. Quality may be affected." |
| **Low resolution (<150 DPI)** | Image metadata check | Process with warning | "⚠ Low resolution detected. OCR confidence may be reduced." |
| **Mixed orientation pages** | Per-page detection | Rotate each page independently | "Pages {list} auto-rotated." |
| **Large file (>50MB)** | File size check | Reject or chunk processing | "File exceeds 50MB limit. Consider splitting document." |
| **Non-medical content** | Heuristic detection | Process with warning | "⚠ Document may not be medical record (low medical term density)." |
| **Blank pages** | OCR confidence = 0 | Skip page, log in metadata | "Pages {list} appear blank and were skipped." |
| **Handwritten-only pages** | Layout analysis | Flag for high uncertainty | "⚠ Page {n}: Handwriting-only, confidence may be low." |
| **Multi-column layout** | Layout detection | Preserve column order | "Multi-column layout detected on page {n}." |
| **Tables with handwriting** | Layout + content analysis | Best-effort structure preservation | "⚠ Handwritten table on page {n} may have reduced accuracy." |
| **Stamps/seals over text** | OCR confidence drop | Extract readable portions | "Page {n}: Text partially obscured by stamp/seal." |
| **Faded/low contrast** | Image analysis | Enhance contrast pre-OCR | "Low contrast detected. Applied enhancement." |

### OCR Processing Edge Cases

| Edge Case | Detection | Handling | Output |
|-----------|-----------|----------|--------|
| **Confidence < 70%** | Per-page score | Flag entire page for review | `"manual_review_required": true` |
| **Mixed languages** | Character set analysis | Process all, note non-English | `"contains_non_english": true, "languages": ["en", "es"]` |
| **Medical symbols** | Character recognition | Preserve Unicode symbols | `"↑ ↓ ± ≥ ≤"` in raw_text |
| **Illegible sections** | Confidence < 40% | Mark as `[UNCLEAR]` | `"[UNCLEAR: partial_text_if_any]"` |
| **Overlapping text** | Layout conflict detection | Extract both, note overlap | `"overlapping_text_detected": true` |
| **No text detected** | Empty OCR result | Return empty with warning | `"raw_text": "", "warning": "No text detected"` |

### Data Extraction Edge Cases

| Edge Case | Detection | Handling | Output |
|-----------|-----------|----------|--------|
| **No patient name found** | Field validation | Set to null, flag warning | `"patient_name": null, "warnings": ["Patient name not found"]` |
| **Multiple patient names** | Name extraction conflicts | Flag for manual review | `"manual_review_required": true, "review_reasons": ["Multiple patient names detected"]` |
| **Conflicting dates** | Cross-validation | Use earliest, log conflict | `"date_conflict_detected": true, "conflicting_dates": [...]` |
| **Future dates** | Date validation | Reject, flag for review | `"errors": ["Visit date {date} is in the future"]` |
| **Invalid date formats** | Parsing errors | Attempt multiple formats, fallback to text | `"visit_date": null, "visit_date_raw": "12/??/2024"` |
| **Missing units** | Value without unit detection | Flag, attempt inference from context | `"unit": null, "unit_inferred": "mg/dL", "confidence": 0.6` |
| **Out-of-range vitals** | Range validation | Accept but flag | `"abnormal_flag": "out_of_range", "expected_range": "40-300 mmHg"` |
| **Duplicate visits same date** | Date collision | Merge or separate based on content similarity | `"visit_id": "visit_001a", "visit_id": "visit_001b"` |
| **Ambiguous abbreviations** | Medical term resolution | Use context, flag if ambiguous | `"abbreviation_expansions": {"MS": ["Multiple Sclerosis", "Mitral Stenosis"]}` |
| **Incomplete medication info** | Required field missing | Include partial data, flag incompleteness | `"medications": [{"name": "Aspirin", "dose": null, "warnings": ["Dose not specified"]}]` |
| **Unrecognized medical codes** | Code validation | Accept but warn | `"icd10_code": "X99.9", "code_validation": "Code not recognized, may be invalid"` |

### System-Level Edge Cases

| Edge Case | Detection | Handling | Recovery |
|-----------|-----------|----------|----------|
| **Gemini API timeout** | HTTP timeout | Retry with exponential backoff (3 attempts) | Max 30s wait, then fail gracefully |
| **Gemini API rate limit** | 429 HTTP status | Wait and retry per Retry-After header | Queue requests, inform user of delay |
| **Gemini API error** | 5xx HTTP status | Retry 3x, then fail with error message | Log error, suggest retry later |
| **Out of memory** | Memory monitoring | Chunk processing, reduce batch size | Process page-by-page if needed |
| **Disk space exhausted** | Storage check | Reject new uploads | "Insufficient disk space. Please free up space." |
| **Processing timeout (>5min)** | Timer | Cancel, return partial results | "Processing timeout. Partial results available." |
| **Schema validation failure** | JSON schema check | Log errors, attempt best-effort output | "Output may not conform to schema. See errors." |
| **XML generation failure** | Template rendering error | Return JSON only, log error | "XML generation failed. JSON output available." |

---

## 10. Performance & Scalability

### Performance SLAs (Single Document)

| Document Size | OCR Time (Target) | Total Processing (Target) | Max Acceptable |
|---------------|-------------------|---------------------------|----------------|
| 1-5 pages | <30s | <60s | 2 minutes |
| 6-20 pages | <90s | <3 minutes | 5 minutes |
| 21-50 pages | <3 minutes | <6 minutes | 10 minutes |
| 51-100 pages | <6 minutes | <12 minutes | 20 minutes |

**Note:** Times assume reasonable quality scans (200+ DPI) and normal API latency.

### Resource Limits

```python
# Configuration
MAX_FILE_SIZE_MB = 50
MAX_PAGE_COUNT = 100
MAX_MEMORY_PER_DOCUMENT_GB = 2
MAX_CONCURRENT_DOCUMENTS = 1  # Phase 1 limitation

OCR_TIMEOUT_PER_PAGE_SEC = 30
STRUCTURING_TIMEOUT_SEC = 120

# Gemini API Rate Limits (as of 2025)
GEMINI_REQUESTS_PER_MINUTE = 60
GEMINI_TOKENS_PER_MINUTE = 4_000_000
```

### Retry & Backoff Strategy

```python
# Exponential backoff for transient errors
MAX_RETRIES = 3
INITIAL_BACKOFF_SEC = 1
MAX_BACKOFF_SEC = 32
BACKOFF_MULTIPLIER = 2

# Retry conditions
RETRYABLE_ERRORS = [
    "timeout",
    "rate_limit_exceeded",
    "internal_server_error",
    "service_unavailable"
]

# Non-retryable errors (fail fast)
FATAL_ERRORS = [
    "invalid_api_key",
    "quota_exceeded",
    "malformed_request"
]
```

### Memory Management

```python
# Chunking strategy for large documents
if page_count > 50:
    # Process in batches of 10 pages
    batch_size = 10
    process_in_batches(pages, batch_size)

# Cleanup after each document
def cleanup():
    - Clear temporary files
    - Release PDF handles
    - Garbage collect large objects
    - Reset processing state
```

---

## 11. Observability & Debugging

### Structured Logging

**Log Levels:**
- `DEBUG`: Detailed processing steps (disabled in production)
- `INFO`: Normal operations (document start/complete)
- `WARN`: Recoverable issues (low confidence, missing data)
- `ERROR`: Processing failures (API errors, validation failures)
- `CRITICAL`: System failures (out of memory, disk full)

**Log Schema:**
```json
{
  "timestamp": "2025-12-19T10:30:00.123Z",
  "level": "INFO|WARN|ERROR",
  "trace_id": "uuid-v4",
  "document_id": "doc_uuid",
  "component": "ocr|chunking|structuring|rendering",
  "message": "Human-readable message",
  "metadata": {
    "page_number": 3,
    "confidence_score": 0.85,
    "processing_time_ms": 1234
  },
  "error": {
    "type": "ValidationError",
    "message": "Field 'patient_name' exceeds max length",
    "stack_trace": "..."
  }
}
```

### Metrics Collection

**Key Metrics:**
```python
# Processing Metrics
- documents_processed_total (counter)
- processing_duration_seconds (histogram)
- pages_processed_total (counter)
- ocr_confidence_score (histogram)
- api_calls_total (counter, labeled by model)
- api_errors_total (counter, labeled by error_type)

# Quality Metrics
- documents_requiring_review_total (counter)
- unclear_sections_per_document (histogram)
- schema_validation_failures_total (counter)

# System Metrics
- memory_usage_bytes (gauge)
- disk_usage_bytes (gauge)
- active_processing_jobs (gauge)
```

### Trace IDs
- **UUID v4** assigned to each document at upload
- Propagated through entire pipeline
- Included in all logs, outputs, and error messages
- Enables end-to-end debugging

### Debug Mode Output

When `DEBUG=True`:
```python
output_files = {
    "canonical.json": {...},
    "ccd.xml": "...",
    "human_readable.pdf": bytes,

    # Debug outputs
    "debug/ocr_raw_pages.json": [...],  # Raw OCR per page
    "debug/chunking_decisions.json": {...},  # Why chunks were created
    "debug/deduplication_log.json": [...],  # What was merged
    "debug/confidence_map.json": {...},  # Confidence per field
    "debug/processing_timeline.json": [...]  # Step-by-step timing
}
```

---

## 12. Streamlit UI Specification

### UI Flow

```
┌─────────────────────────────────────────────┐
│           Medical PDF Processor             │
└─────────────────────────────────────────────┘

Step 1: Upload Document
┌─────────────────────────────────────────────┐
│  📄 Drag & drop PDF or click to browse      │
│                                             │
│  Accepted: .pdf files up to 50MB           │
│  Max pages: 100                             │
└─────────────────────────────────────────────┘

Step 2: Document Preview
┌─────────────────────────────────────────────┐
│  ✅ my_medical_record.pdf                   │
│     • Size: 12.3 MB                         │
│     • Pages: 15                             │
│     • Quality: Good (300 DPI)               │
│                                             │
│  [Process Document] [Cancel]                │
└─────────────────────────────────────────────┘

Step 3: Processing (Real-time Progress)
┌─────────────────────────────────────────────┐
│  Processing: 60% complete                   │
│  ████████████░░░░░░░░                       │
│                                             │
│  Current step: OCR Processing               │
│  • Page 9/15 complete                       │
│  • Avg confidence: 92%                      │
│  • Estimated time remaining: 45s            │
│                                             │
│  Logs:                                      │
│  [10:30:15] Started OCR processing          │
│  [10:30:32] Page 5: Low contrast detected   │
│  [10:31:05] Chunking: 3 visits identified   │
└─────────────────────────────────────────────┘

Step 4: Results & Download
┌─────────────────────────────────────────────┐
│  ✅ Processing Complete!                    │
│                                             │
│  Document Quality:                          │
│  • Overall confidence: 92%                  │
│  • Visits identified: 3                     │
│  • Warnings: 2 (see details below)          │
│                                             │
│  Download Outputs:                          │
│  📥 [Download JSON]                         │
│  📥 [Download CCD XML]                      │
│  📥 [Download PDF Report]                   │
│  📥 [Download DOCX Report]                  │
│  📥 [Download Debug Bundle] (if enabled)    │
│                                             │
│  ⚠ Warnings:                                │
│  • Page 7: Handwriting confidence 68%       │
│  • Medication dose unclear on page 12       │
│                                             │
│  [Process Another Document]                 │
└─────────────────────────────────────────────┘
```

### UI Features

**Upload Validation:**
- Client-side file type check (.pdf only)
- File size check (50MB limit with clear error)
- Immediate feedback on invalid files

**Progress Indicators:**
- Real-time progress bar (updated every 2s)
- Current step display
- Page-by-page progress for OCR
- Time estimates (based on page count)

**Error Handling:**
- Clear, non-technical error messages
- Suggested actions for common errors
- Option to download partial results if processing fails mid-way

**Download Options:**
- Individual file downloads
- "Download All" button (ZIP archive)
- Preview JSON/XML in browser before download

**Accessibility:**
- Keyboard navigation support
- Screen reader compatible labels
- High contrast mode option

---

## 13. Security & Privacy

### Data Handling Guarantees

**Storage:**
- ✅ Files processed **in-memory** where possible
- ✅ Temporary disk storage **only** if file > 100MB
- ✅ Automatic cleanup after processing (max 1 hour retention)
- ✅ No database storage
- ✅ No cloud sync

**API Communication:**
- ✅ HTTPS only for Gemini API calls
- ✅ API keys stored in environment variables (never in code)
- ✅ No data sent to non-Google services
- ✅ Gemini API: Data not used for training (per Google Cloud terms)

**Access Control:**
- ✅ Local-only deployment (127.0.0.1 binding)
- ✅ No network exposure
- ✅ No authentication (single-user assumption)
- ✅ Session-based isolation (if multi-session)

### HIPAA Considerations (Even for Local Use)

Although this is local deployment, follow HIPAA-aligned practices:
- **Minimum Necessary:** Only extract data required for CCD generation
- **Audit Logging:** Log all processing activities (optional, configurable)
- **Data Disposal:** Secure deletion of temporary files (overwrite before delete)
- **No Identifiable Data in Logs:** Redact patient names from logs (optional flag)

### Dependency Security

```bash
# Regular security audits
pip audit  # Check for known vulnerabilities

# Pin all dependencies
requirements.txt with exact versions (==, not >=)

# Monthly dependency updates with testing
```

---

## 14. Testing Strategy

### Test Pyramid

```
                 ┌────────────┐
                 │   E2E (5)  │  Real PDFs, full pipeline
                 └────────────┘
              ┌──────────────────┐
              │ Integration (20) │  Component combinations
              └──────────────────┘
         ┌──────────────────────────┐
         │    Unit Tests (100+)     │  Individual functions
         └──────────────────────────┘
```

### Unit Tests (100+ tests)

**Coverage Target:** 85%+ for core logic

**Critical Test Cases:**
- Schema validation (valid/invalid inputs)
- Deduplication logic (exact/fuzzy/edge cases)
- Date parsing (multiple formats, invalid dates)
- Unit conversion (metric/imperial)
- Error handling (all error types)
- Edge case handling (each edge case documented)

```python
# Example test structure
def test_fuzzy_deduplication():
    assert merge_problems("Hypertension", "HTN") == {
        "problem": "Hypertension",
        "alternatives": ["HTN"],
        "confidence": 0.85
    }

def test_date_parsing_ambiguous():
    # 01/02/2025 could be Jan 2 or Feb 1
    result = parse_date("01/02/2025")
    assert result["ambiguous"] == True
    assert result["interpretations"] == ["2025-01-02", "2025-02-01"]
```

### Integration Tests (20 tests)

**Test Scenarios:**
- OCR → Chunking → Structuring (full pipeline)
- JSON → XML rendering (template correctness)
- JSON → Human-readable rendering
- Error propagation across components
- Retry logic (mocked API failures)

### End-to-End Tests (5 golden datasets)

**Golden Dataset Requirements:**
1. **Simple handwritten note** (1-2 pages, single visit)
2. **Typed discharge summary** (5 pages, structured)
3. **Mixed handwritten + printed** (10 pages, multiple visits)
4. **Lab results only** (3 pages, tables)
5. **Complex multi-visit** (20+ pages, edge cases)

**Validation:**
- Expected JSON output (human-reviewed ground truth)
- Schema conformance
- XML validation
- Performance benchmarks

**Regression Testing:**
- All golden datasets run on every commit
- Output compared to baseline (JSON diff)
- Alert on unexpected changes

### Clinical Validation Process

**Phase 1 (Internal):**
1. Process 50 real medical records (anonymized)
2. Clinical reviewer spot-checks 20% of outputs
3. Document accuracy rate per section type
4. Identify systemic extraction issues

**Phase 2 (User Acceptance):**
1. Client processes 10 documents from their workflow
2. Feedback on accuracy, usability, output format
3. Iterate on issues found
4. Sign-off on production readiness

---

## 15. Schema Evolution & Versioning

### Schema Versioning
```json
{
  "schema_version": "2.0",  // Semantic versioning
  "backward_compatible_with": ["1.0", "1.1"]
}
```

### Migration Strategy

**Adding Fields (Minor Version):**
- New optional fields → minor version bump (2.0 → 2.1)
- Backward compatible (old consumers ignore new fields)

**Removing/Renaming Fields (Major Version):**
- Breaking changes → major version bump (2.1 → 3.0)
- Provide migration script
- Support N-1 version for 6 months

**Example Migration:**
```python
def migrate_v1_to_v2(old_json):
    new_json = deepcopy(old_json)
    new_json["schema_version"] = "2.0"

    # Add new fields with defaults
    new_json["data_quality"] = {
        "completeness_score": calculate_completeness(old_json),
        "confidence_score": 0.0,  # Not available in v1
        "unclear_sections": []
    }

    return new_json
```

---

## 16. Dependencies & Infrastructure

### Python Environment
```
Python Version: 3.10+ (recommend 3.11 for performance)
Virtual Environment: Required (venv or conda)
```

### Core Dependencies

```txt
# requirements.txt (pinned versions)

# PDF Processing
pypdf==4.0.1
pdf2image==1.17.0
Pillow==10.2.0

# Google Gemini
google-generativeai==0.3.2
google-cloud-aiplatform==1.41.0

# Data Validation & Schema
pydantic==2.5.3
jsonschema==4.20.0

# XML Processing
lxml==5.1.0
xmlschema==3.0.2

# Document Generation
reportlab==4.0.9  # PDF generation
python-docx==1.1.0  # DOCX generation
jinja2==3.1.3  # Templating

# UI
streamlit==1.30.0

# Utilities
python-dateutil==2.8.2
python-dotenv==1.0.1
requests==2.31.0
tenacity==8.2.3  # Retry logic

# Logging & Monitoring
structlog==24.1.0

# Testing
pytest==7.4.4
pytest-cov==4.1.0
pytest-mock==3.12.0

# Code Quality
black==24.1.1
ruff==0.1.15
mypy==1.8.0
```

### API Dependencies

**Gemini API:**
- API Key: Required (Google AI Studio or Cloud)
- Quota: Check https://ai.google.dev/pricing
- Models:
  - `gemini-3-preview` (vision OCR)
  - `gemini-2.5-flash` (structured extraction)

**Fallback Strategy (if Gemini unavailable):**
- Use Tesseract OCR (lower quality) for OCR
- Use rule-based extraction (limited medical intelligence)
- Clearly mark outputs as "fallback mode"

### System Requirements

**Minimum:**
- CPU: 4 cores
- RAM: 8GB
- Disk: 10GB free space
- OS: Linux, macOS, Windows 10+

**Recommended:**
- CPU: 8+ cores (faster parallel processing)
- RAM: 16GB (large documents)
- Disk: 50GB free (temporary file storage)
- SSD strongly recommended

---

## 17. Documentation Requirements

### User Documentation

**README.md:**
- Project overview
- Installation instructions
- Quick start guide
- Configuration options
- Troubleshooting common issues

**USER_GUIDE.md:**
- Detailed usage instructions
- UI walkthrough with screenshots
- Input preparation best practices
- Output interpretation guide
- FAQ

### Developer Documentation

**ARCHITECTURE.md:**
- System architecture diagram
- Component descriptions
- Data flow
- Design decisions & rationale

**API_REFERENCE.md:**
- Internal API documentation (even if not exposed)
- Function signatures
- Input/output schemas
- Error codes

**CONTRIBUTING.md:**
- Code style guide
- Testing requirements
- Pull request process
- Development setup

### Operational Documentation

**DEPLOYMENT.md:**
- Environment setup
- Dependency installation
- Configuration
- Running the application

**TROUBLESHOOTING.md:**
- Common errors and solutions
- Performance optimization tips
- Log interpretation
- When to contact support

**ERROR_CATALOG.md:**
- All error codes
- Error descriptions
- Suggested user actions
- Technical details for debugging

---

## 18. Compliance & Regulatory

### Medical Software Considerations

**Not a Medical Device (Current Scope):**
- This is a **documentation tool**, not a diagnostic tool
- Does NOT provide treatment recommendations
- Does NOT make clinical decisions
- **Consult legal/compliance before use in regulated healthcare environments**

**Data Accuracy Disclaimer:**
```
IMPORTANT: This system is a documentation aid for extracting information
from scanned medical records. All outputs should be reviewed by qualified
healthcare professionals. Do not use this system as the sole source of
patient information for clinical decision-making.

Accuracy limitations:
- OCR may misread handwritten text
- Missing or unclear sections are marked but may be incomplete
- Medical abbreviations may be ambiguous
- This system does not validate medical correctness

Always refer to original source documents for critical decisions.
```

### Validation Documentation (For Clinical Use)

If used in clinical workflows, maintain:
- **Accuracy Studies:** Documented accuracy rates per section type
- **Validation Report:** Testing methodology and results
- **Known Limitations:** Explicit list of system limitations
- **Version Control:** All software versions used in production

---

## 19. Milestone Breakdown (Contract-Aligned)

### ✅ Milestone 1: Core Pipeline

**Deliverables:**
1. PDF ingestion and validation
2. Gemini 3 Preview OCR integration
3. Raw OCR → structured pages (JSON)
4. Chunking engine (visit detection)
5. Canonical JSON schema (validated)
6. Unit tests (60%+ coverage)

**Acceptance Criteria:**
- Process 5-page handwritten PDF → valid JSON
- Schema validation passes
- Confidence scoring works
- Edge cases handled gracefully

---

### ✅ Milestone 2: Rendering & UI

**Deliverables:**
1. Gemini 2.5 Flash medical structuring
2. Deduplication & merge logic
3. JSON → CCD XML renderer (validated)
4. JSON → Human-readable (PDF/DOCX)
5. Streamlit UI (upload → download)
6. Integration tests
7. End-to-end golden dataset validation

**Acceptance Criteria:**
- XML validates against CCD schema
- Human-readable output is professionally formatted
- UI is functional and user-friendly
- All 5 golden datasets pass
- Performance meets SLAs

---

### 🔄 Milestone 3: Production Hardening

**Deliverables:**
1. Comprehensive error handling
2. Logging and observability
3. Performance optimization
4. Documentation (user guide + architecture)
5. Testing and validation
6. Deployment package

**Acceptance Criteria:**
- 85%+ test coverage
- All documentation complete
- Client sign-off on functionality
- Zero critical bugs
- Performance benchmarks met

---

## 20. Non-Negotiable Engineering Rules

### 1. Zero Hallucination Policy
```python
# ❌ NEVER DO THIS
if not patient_name:
    patient_name = "John Doe"  # FORBIDDEN

# ✅ ALWAYS DO THIS
if not patient_name:
    patient_name = None
    warnings.append("Patient name not found in document")
```

### 2. Single Source of Truth
```python
# ❌ NEVER DO THIS
def generate_xml(pdf):
    # Extract data directly for XML
    ...

# ✅ ALWAYS DO THIS
def generate_xml(canonical_json):
    # Render from JSON only
    ...
```

### 3. Explicit Uncertainty
```python
# ❌ NEVER DO THIS
medication = "Asprin"  # Silently corrected from OCR

# ✅ ALWAYS DO THIS
medication = "Asprin [UNCLEAR: possible 'Aspirin']"
```

### 4. Fail Loudly
```python
# ❌ NEVER DO THIS
try:
    process_document()
except Exception:
    pass  # Silent failure

# ✅ ALWAYS DO THIS
try:
    process_document()
except Exception as e:
    logger.error(f"Processing failed: {e}", exc_info=True)
    raise ProcessingError("Document processing failed") from e
```

### 5. Immutable Outputs
```python
# Once JSON is generated, XML/PDF are pure renders
# NO additional data extraction in rendering phase
```

---

## 21. Definition of Done (Production-Ready Checklist)

### Functional Requirements
- [ ] Processes multi-page handwritten PDFs (1-100 pages)
- [ ] Processes printed PDFs
- [ ] Processes mixed handwritten + printed PDFs
- [ ] Handles all edge cases documented in Section 9
- [ ] Outputs valid canonical JSON (schema v2.0)
- [ ] Outputs valid CCD/CCDA XML
- [ ] Outputs professional PDF report
- [ ] Outputs editable DOCX report
- [ ] Streamlit UI functional (upload → download)
- [ ] All 5 golden datasets pass validation

### Non-Functional Requirements
- [ ] Performance meets SLAs (Section 10)
- [ ] Memory usage within limits
- [ ] No crashes on valid inputs
- [ ] Graceful degradation on invalid inputs
- [ ] Deterministic output (same input → same output)
- [ ] Repeatable results across runs

### Code Quality
- [ ] 85%+ unit test coverage
- [ ] 20 integration tests pass
- [ ] 5 E2E tests pass
- [ ] Code passes linting (ruff, black)
- [ ] Type hints complete (mypy passes)
- [ ] No critical security vulnerabilities (pip audit)
- [ ] Clean separation of concerns (OCR ≠ structuring ≠ rendering)

### Documentation
- [ ] README.md complete
- [ ] USER_GUIDE.md complete
- [ ] ARCHITECTURE.md complete
- [ ] API_REFERENCE.md complete
- [ ] TROUBLESHOOTING.md complete
- [ ] ERROR_CATALOG.md complete
- [ ] Inline code comments for complex logic

### Validation & Sign-Off
- [ ] Internal testing complete with sample documents
- [ ] Edge case handling verified
- [ ] Client UAT: Representative documents processed successfully
- [ ] Client sign-off received

### Deployment Readiness
- [ ] Installation instructions tested on fresh environment
- [ ] Dependencies pinned and documented
- [ ] Environment variables documented
- [ ] Runbook created
- [ ] Handoff complete

---

## 22. Future Enhancements (Out of Scope for Phase 1)

### Phase 2 Possibilities
- REST API exposure (FastAPI)
- Multi-user support with auth
- Batch processing UI
- Progress API (websocket)
- OCR correction interface (human-in-the-loop)
- Integration with EHR systems (HL7 FHIR)

### Phase 3 Possibilities
- Cloud deployment (HIPAA-compliant)
- Fine-tuned models for specific medical specialties
- Support for non-English medical records
- Advanced deduplication (ML-based)
- Automated medical code assignment (ICD-10, CPT)

---

## 23. Contact & Support

**Project Owner:** Krupali Surani
**Technical Lead:** [TBD]
**Repository:** [GitHub URL]
**Issue Tracking:** GitHub Issues
**Documentation:** /docs folder

---

**Document Control:**
- Version: 2.0
- Last Updated: 2025-12-19
- Next Review: Upon Phase 1 Completion
- Approved By: [Pending Client Sign-Off]

---

**CRITICAL REMINDERS:**
1. **NO HALLUCINATION** - If data is unclear, mark it [UNCLEAR]
2. **JSON IS SOURCE OF TRUTH** - All outputs render from JSON
3. **PRESERVE ORIGINAL MEANING** - No silent corrections
4. **FAIL LOUDLY** - Never suppress errors
5. **DETERMINISTIC** - Same input = same output, always
