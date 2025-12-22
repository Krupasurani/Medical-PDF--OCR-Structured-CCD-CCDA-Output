# 🖥️ Running the Streamlit UI

**Interactive Medical PDF Processor Interface**

---

## 🚀 Quick Start

```bash
# 1. Ensure virtual environment is activated
source venv/bin/activate  # Mac/Linux
# OR
venv\Scripts\activate  # Windows

# 2. Ensure API key is configured in .env
cat .env  # Should show GEMINI_API_KEY=...

# 3. Launch the UI
streamlit run app.py
```

The app will automatically open in your default browser at `http://localhost:8501`

---

## 📋 Step-by-Step User Guide

### Step 1: Upload Document

1. **Click "Choose a medical PDF file"** or drag-and-drop
2. Select your scanned medical PDF
3. Wait for upload confirmation (green checkmark)

**Accepted Files:**
- Format: PDF only
- Max Size: 50 MB
- Max Pages: 100
- Best Quality: 200+ DPI

**What Happens:**
- Client-side validation (file type, size)
- File preview with metadata
- Ready for processing

---

### Step 2: Process Document

1. **Click "🚀 Process Document"** button
2. Watch real-time progress (6 steps):
   - Step 1/6: Validating PDF
   - Step 2/6: OCR Processing (page-by-page)
   - Step 3/6: Identifying visits
   - Step 4/6: Structuring medical data
   - Step 5/6: Deduplicating data
   - Step 6/6: Generating outputs

**Progress Indicators:**
- Live progress bar (0-100%)
- Current step display
- Page-by-page status for OCR
- Estimated time remaining

**Processing Times:**
- 1-5 pages: ~30-60 seconds
- 6-20 pages: ~2-3 minutes
- 21-50 pages: ~5-6 minutes

**What Happens:**
1. **PDF Validation**: Checks page count, file integrity
2. **OCR**: Gemini 3 Pro extracts text from each page
3. **Chunking**: Detects visit boundaries
4. **Structuring**: Gemini 2.5 Flash creates canonical JSON
5. **Deduplication**: Merges duplicate data (medications, problems, labs)
6. **Rendering**: Generates XML, PDF, DOCX from JSON

---

### Step 3: Review Results

After processing completes, you'll see:

#### Quality Dashboard

**Metrics:**
- **Processing Time**: Total time taken (seconds)
- **Pages Processed**: Number of pages analyzed
- **Visits Identified**: Number of clinical encounters detected
- **OCR Confidence**: Average confidence (0-100%)

**Indicators:**
- 🟢 Green (90-100%): Excellent quality
- 🟡 Yellow (70-89%): Good quality, review recommended
- 🔴 Red (<70%): Low quality, manual review required

#### Warnings Section

**Quality Warnings** (⚠️ Yellow Box):
- Low confidence pages
- Unclear sections
- Missing data

**Example:**
```
⚠️ Quality Warnings
• Page 7: Handwriting confidence 68%
• Medication dose unclear on page 12
```

**Manual Review Flags** (⚠️ Yellow Box):
- Visits requiring human review
- Reasons for review (low confidence, missing data, conflicts)

**Example:**
```
⚠️ 1 visit(s) require manual review
• Visit visit_001: Handwriting illegible, missing critical fields
```

---

### Step 4: Download Outputs

Five download buttons appear after successful processing:

#### 📥 Download JSON
**File:** `{filename}_canonical.json`
**Purpose:** Structured medical data (source of truth)
**Use:** API integration, data analysis, audit trails
**Size:** Typically 10-100 KB

**Contents:**
- Complete medical document structure
- All visits with medications, problems, vitals, labs
- Data quality metrics
- Source page tracking

#### 📥 Download OCR
**File:** `{filename}_ocr.txt`
**Purpose:** Raw OCR text (all pages)
**Use:** Debugging, manual review, text search
**Size:** Typically 5-50 KB

**Contents:**
- Page-by-page OCR output
- Separated by page headers (PAGE 1, PAGE 2, etc.)
- Unstructured text as extracted

#### 📥 Download XML
**File:** `{filename}_ccd.xml`
**Purpose:** CCD/CCDA-compatible clinical document
**Use:** EHR integration, health information exchange
**Size:** Typically 20-150 KB

**Contents:**
- HL7-formatted clinical document
- Patient demographics
- Structured clinical sections
- LOINC-coded sections

#### 📥 Download PDF
**File:** `{filename}_report.pdf`
**Purpose:** Professional medical report
**Use:** Printing, clinical review, patient records
**Size:** Typically 100-500 KB

**Contents:**
- Professional medical document layout
- Patient demographics header
- Visit summaries with tables
- Data quality notes

#### 📥 Download DOCX
**File:** `{filename}_report.docx`
**Purpose:** Editable Word document
**Use:** Clinical review, annotation, editing
**Size:** Typically 50-200 KB

**Contents:**
- Editable text and tables
- Consistent styling with PDF
- Supports comments and revisions

---

## 🎨 UI Features

### Sidebar Information

**Contains:**
- How to Use guide
- Accepted file specifications
- Privacy notice (local processing)
- Version information

**Privacy Guarantee:**
- All processing is local
- Files NOT stored
- Temporary files auto-deleted
- No cloud sync

### Real-Time Progress

**Updates Every 2 Seconds:**
- Progress percentage
- Current step name
- Page progress (during OCR)
- Time estimates

**Example:**
```
Processing: 60% complete
████████████░░░░░░░░

Current step: OCR Processing
• Page 9/15 complete
• Avg confidence: 92%
• Estimated time remaining: 45s
```

### Error Handling

**Clear Error Messages:**
- Non-technical language
- Suggested actions
- Option to view details

**Example Errors:**
```
❌ Processing failed: PDF has 150 pages (max 100 allowed)
Suggested action: Split document into smaller files

❌ Processing failed: API timeout
Suggested action: Check internet connection, try again
```

**Error Details Expander:**
- Click "Show error details" for stack trace
- Technical information for debugging
- Helpful for support requests

---

## 🔧 Advanced Options

### Custom Port

If port 8501 is already in use:

```bash
streamlit run app.py --server.port 8502
```

### Remote Access

**NOT RECOMMENDED for medical data (HIPAA concerns)**

If you must enable remote access (e.g., within secure network):

```bash
streamlit run app.py --server.address 0.0.0.0
```

**Security Warning:** Only use on trusted, secure networks. Medical data should NOT be transmitted over public networks.

### Debug Mode

Enable detailed logging:

```bash
# In .env file
DEBUG=true

# Then run
streamlit run app.py
```

Logs will show in console with detailed processing steps.

---

## 🐛 UI Troubleshooting

### "Address already in use"

**Problem:** Port 8501 is occupied

**Solutions:**
1. Stop other Streamlit apps
2. Use different port: `streamlit run app.py --server.port 8502`
3. Restart computer (kills all processes)

### "Module not found" Errors

**Problem:** Dependencies not installed

**Solutions:**
1. Ensure virtual environment is activated:
   ```bash
   source venv/bin/activate  # Mac/Linux
   venv\Scripts\activate     # Windows
   ```
2. Reinstall dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### UI Freezes During Processing

**Problem:** Browser timeout or connection issue

**Solutions:**
1. **Wait patiently** - Large PDFs take time (up to 10 minutes for 50+ pages)
2. Check console logs for progress
3. Refresh page (processing continues on server)
4. If truly stuck, restart app (Ctrl+C, then rerun)

### Downloads Not Working

**Problem:** Browser blocking downloads or permissions issue

**Solutions:**
1. Check browser download settings
2. Ensure popup blocker is disabled
3. Try different browser (Chrome, Firefox work best)
4. Check disk space

### Low OCR Confidence Warning

**Problem:** Original document quality is poor

**Solutions:**
1. **Re-scan document** at higher DPI (300+ recommended)
2. **Manually review** flagged sections
3. **Accept results** if confidence is above 70% (usually acceptable)

### "Processing Timeout" Error

**Problem:** Document too large or API latency

**Solutions:**
1. **Split document** into smaller files
2. **Check internet connection** (Gemini API requires stable connection)
3. **Retry** - temporary API issues
4. **Use CLI instead** (main.py) for better timeout control

---

## 📊 Understanding Results

### Confidence Scores

**Page-Level Confidence:**
- How certain OCR is about extracted text
- 90-100%: Excellent (typed documents)
- 70-89%: Good (clear handwriting)
- 50-69%: Fair (unclear handwriting, review recommended)
- <50%: Poor (manual review required)

**Document-Level Confidence:**
- Average of all page confidences
- Same thresholds as page-level

**What Affects Confidence:**
- Document quality (DPI, clarity)
- Handwriting legibility
- Image artifacts (stains, tears, fading)
- Mixed text types (printed + handwritten)

### Visit Detection

**How Visits Are Identified:**
- Date-based separation
- Document structure changes
- Encounter type indicators
- Page breaks with new headers

**Common Scenarios:**
- 1 visit: Single encounter document
- 2-5 visits: Multiple follow-ups
- 10+ visits: Comprehensive medical history

**Review Needed If:**
- Visits incorrectly split (combine manually)
- Single visit split into multiple (merge in JSON)
- Missing visit boundaries (add separators in source)

### Data Quality Notes

**Completeness Score:**
- Percentage of expected fields with data
- 90-100%: Complete record
- 70-89%: Some missing fields
- <70%: Incomplete record

**Unclear Sections:**
- Specific sections with low confidence
- Reasons provided (handwriting illegible, faded text, etc.)
- Original text shown where possible

**Missing Critical Fields:**
- Patient name, DOB, visit date
- Flagged for manual entry
- Check original document

---

## 💡 Best Practices

### Document Preparation

**Before Upload:**
1. **Scan at 300 DPI** (minimum 200 DPI)
2. **Ensure pages are straight** (not skewed)
3. **Remove blank pages**
4. **Check file size** (<50 MB)
5. **Combine related visits** into single PDF

### Review Process

**After Processing:**
1. **Check confidence scores** (>70% target)
2. **Review warnings** (address unclear sections)
3. **Spot-check critical data** (medications, allergies)
4. **Compare with original** (random page sampling)
5. **Mark manual review items** for clinical staff

### Clinical Workflow

**Recommended Workflow:**
1. **Batch Upload**: Process multiple documents at once (use CLI for automation)
2. **Triage Review**: Focus on low-confidence documents
3. **Clinical Review**: Healthcare professional validates structured data
4. **EHR Import**: Use JSON or XML for system integration
5. **Archive**: Keep original PDFs + JSON for audit

---

## 🎓 Training Users

### For Non-Technical Users

**Key Points:**
- Upload → Process → Download (3 clicks)
- Wait for green checkmark before downloading
- Pay attention to yellow warnings
- Download all 5 files for complete record

**Demo Script:**
```
1. "Let me show you how to process a medical record..."
2. "Click here to upload... see the file name and size?"
3. "Now click Process Document... watch the progress bar"
4. "See these metrics? 95% confidence means high quality"
5. "Now download what you need - PDF for printing, DOCX for editing"
```

### For Clinical Staff

**Key Points:**
- Understand confidence scores (what's acceptable)
- Review manual review flags (clinical judgment needed)
- Compare outputs to original (spot-check validation)
- Know when to escalate (unclear critical data)

### For IT Staff

**Key Points:**
- Environment setup (Python, API keys)
- Troubleshooting common issues
- Performance optimization
- Security considerations (HIPAA, PHI)

---

## 📞 Getting Help

### Self-Service

1. **Check logs**: Console output shows detailed progress
2. **Review README.md**: General setup and troubleshooting
3. **Check ARCHITECTURE.md**: Technical design decisions

### Support Contacts

- **Project Owner**: Krupali Surani
- **Technical Lead**: [TBD]
- **Repository**: [GitHub URL]

### Reporting Issues

**Include:**
- Error message (full text)
- Steps to reproduce
- File details (size, pages - NOT actual medical data)
- System info (OS, Python version)
- Logs (if available)

---

## ✅ UI Feature Checklist

**Before Go-Live, Verify:**

- [ ] Streamlit launches without errors
- [ ] File upload works (PDF only, size limits enforced)
- [ ] Progress bar updates in real-time
- [ ] All 5 downloads work
- [ ] Error messages are clear and actionable
- [ ] Warnings display correctly
- [ ] Metrics show accurate data
- [ ] UI is accessible (screen reader, keyboard navigation)
- [ ] Works on all target browsers (Chrome, Firefox, Safari, Edge)
- [ ] Mobile responsive (basic support)

---

**Enjoy the Interactive UI! 🎉**

For command-line usage, see main `README.md`
