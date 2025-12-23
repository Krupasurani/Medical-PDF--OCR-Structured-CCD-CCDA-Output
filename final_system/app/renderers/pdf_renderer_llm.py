"""LLM-Based PDF Renderer for Human-Readable Clinical Summaries

Uses Gemini with detailed prompt to generate professional clinical summaries
from raw OCR text, then renders to PDF using ReportLab.
"""

import google.generativeai as genai
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from ..models.canonical_schema import MedicalDocument
from ..utils.config import get_config
from ..utils.logger import get_logger

logger = get_logger(__name__)


# Human-Readable Summary Generation Prompt
CLINICAL_SUMMARY_PROMPT = """# Human-Readable Clinical Summary Generation

Generate a comprehensive, professional clinical summary from medical OCR text.

**INPUT**: Raw OCR text from medical documents (handwritten + printed notes across multiple pages)

## CRITICAL REQUIREMENTS

1. **Extract ALL clinical information** from ALL pages
2. **Organize chronologically** when dates are available
3. **Preserve clinical uncertainty** - keep "??", "R/O", "Poss.", "[UNCLEAR]" exactly as written
4. **Use professional medical language** - clear, concise, clinical style
5. **Group related information** - combine scattered data into coherent sections
6. **Return ONLY formatted text** - no markdown, use plain text with section headers

---

## CRITICAL FORMATTING RULES

1. **Group lab results by category with organized presentation**:
   - Endocrine Panel, Thyroid Function Tests, etc.
   - Show test name, value, unit, and status/flag
   - Add page references for traceability

2. **Write Assessment as clinical paragraphs** with reasoning, not just bullet points

3. **Include Physical Examination section** organized by system (HEENT, Cardiovascular, etc.)

4. **Organize Plan into clear categories**:
   - Immediate Management
   - Diagnostic Testing (with checkboxes)
   - Patient Instructions
   - Follow-up Schedule

5. **Use visual dividers** between major sections

6. **Add checkboxes** for action items in plan

7. **Show units** for lab values when available (mIU/L, mg/dL, etc.)

---

## OUTPUT FORMAT

Generate output in this EXACT structure:

═══════════════════════════════════════════════════════════════
         CONTINUITY OF CARE DOCUMENT (CCD)
           Medical Consultation Summary - [Specialty from OCR]
═══════════════════════════════════════════════════════════════

PATIENT INFORMATION
  Name:                  [from OCR or "Not recorded"]
  Date of Birth:         [from OCR or "Not recorded"]
  Sex:                   [from OCR or "Not recorded"]
  Medical Record #:      [from OCR or "Not recorded"]

DOCUMENT INFORMATION
  Document Date:         [Extract from OCR or use current date]
  Consultation Type:     [Endocrinology/Cardiology/etc. from OCR]
  Provider:              [from OCR or "OCR Processing System"]
  Organization:          [from OCR or "Medical Records Processing"]
  Pages Processed:       [count] pages

═══════════════════════════════════════════════════════════════


REASON FOR VISIT
────────────────────────────────────────────────────────────────

[Extract chief complaint and reason for visit. Combine all mentions from all pages.
Write as complete sentences/paragraphs, not bullet points.]


HISTORY OF PRESENT ILLNESS
────────────────────────────────────────────────────────────────

[Comprehensive narrative combining information from ALL pages. Include:
- Onset and duration of symptoms
- Patient's description of symptoms
- Relevant timeline
- Associated symptoms
- Aggravating/alleviating factors
Write as flowing paragraphs, preserve exact wording from OCR where clinically important.]


PAST MEDICAL HISTORY
────────────────────────────────────────────────────────────────

• [Condition 1]
• [Condition 2]
• [No history of radiation exposure]
• [etc.]


MEDICATIONS
────────────────────────────────────────────────────────────────

[If present:]
• [Medication name] - [dose] - [frequency] - [route]

[If not documented:]
Not documented in available records


ALLERGIES
────────────────────────────────────────────────────────────────

[List allergies or state "No documented drug allergies" or "Not documented"]


VITAL SIGNS
────────────────────────────────────────────────────────────────

[If present, format as:]
• Blood Pressure: [value] mmHg
• Heart Rate: [value] bpm
• Temperature: [value] °F/°C
• etc.

[If not present:]
Not documented in current extraction


ACTIVE PROBLEMS / DIAGNOSES
────────────────────────────────────────────────────────────────

[List all problems from ALL pages, numbered. Preserve uncertainty markers:]
1. ?? [Problem with uncertainty]
2. R/O [Rule-out diagnosis]
3. Poss. [Possible diagnosis]
4. [Confirmed diagnosis]


LABORATORY RESULTS & DIAGNOSTIC TESTS
────────────────────────────────────────────────────────────────

[Group by category. Format each category as organized table-like structure:]

Endocrine Panel (Page X):
  Test Name                          Value        Status
  ──────────────────────────────────────────────────────
  [Test 1]                           [val] [unit] [Normal/↑/↓]
  [Test 2]                           [val] [unit] [Normal/↑/↓]

  [Notes/comments if any]

Thyroid Function Tests (Page Y):
  Test Name                          Value        Status
  ──────────────────────────────────────────────────────
  TSH                                [val] mIU/L  [Normal]
  Free T3                            [val] pg/mL  [Normal]
  [etc.]

Additional Laboratory Studies (Page Z):
  [Similar format for other tests]

Imaging Studies:
  • [Study name]: [findings] - Page [X]


PHYSICAL EXAMINATION
────────────────────────────────────────────────────────────────

[Extract physical exam findings from ALL pages. Organize by system:]

General:
  [General appearance]

HEENT:
  [Head, eyes, ears, nose, throat findings]

Thyroid:
  [Size, consistency, nodules, bruits, etc.]

Cardiovascular:
  [Heart sounds, murmurs, rhythm]

Respiratory:
  [Lung sounds, breathing]

Abdominal:
  [Tenderness, masses, bowel sounds]

Neurological:
  [Reflexes, strength, tremor, sensation]

Extremities:
  [Edema, pulses, etc.]

Musculoskeletal:
  [Range of motion, deformities]

[If no physical exam documented:]
Physical examination findings not documented in available records


CLINICAL ASSESSMENT & IMPRESSION
────────────────────────────────────────────────────────────────

[Write as clinical paragraphs with reasoning. Group by:]

Primary Diagnostic Considerations:

1. [Primary Diagnosis/Concern]
   [Clinical reasoning paragraph explaining why this is being considered.
   Reference specific findings, labs, symptoms. Explain clinical logic.]

2. [Second Primary Concern]
   [Similar paragraph with clinical reasoning]

Differential Diagnoses Requiring Further Evaluation:

3. Rule Out [Diagnosis]
   [Paragraph explaining what findings suggest this, what tests are needed,
   why it's being considered]

4. [Additional differential]
   [Similar reasoning]

Additional Medical Conditions:

5. [Other relevant diagnoses]
   [Brief clinical context]


TREATMENT PLAN
────────────────────────────────────────────────────────────────

Immediate Management:
  ☐ [Action item 1]
  ☐ [Action item 2]
  ☐ Patient education provided regarding:
    - [Topic 1]
    - [Topic 2]

Diagnostic Testing - Ordered:
  ☐ [Test 1] ([timing if specified])
  ☐ 24-hour urine collection for:
    - [Component 1]
    - [Component 2]
  ☐ [Other tests]

Patient Instructions:
  ☐ [Instruction 1]
  ☐ [Instruction 2]
  ☐ Monitor/check for:
    - [Symptom 1]
    - [Symptom 2]

Equipment/Monitoring:
  ☐ [Any equipment to be provided]

Records/Referrals:
  ☐ [Records to obtain]
  ☐ [Referrals to make]

Follow-up Schedule:
  ☐ Return visit in [timeframe] with:
    - [Required items]
  ☐ [Additional follow-up instructions]
  ☐ Urgent follow-up if [conditions]


────────────────────────────────────────────────────────────────

DOCUMENT GENERATION INFORMATION

  Processing Date:      [Current date and time]
  Processing Method:    OCR with AI-assisted clinical structuring
  OCR Confidence:       [If available from metadata]
  Source Document:      [page count]-page [handwritten/printed] medical notes
  Processing Duration:  [If available]

IMPORTANT NOTES:

  • This document was generated from OCR-processed medical records.
    All critical clinical information should be verified against
    original source documents.

  • For standards-based electronic health record exchange, refer to
    the accompanying CCD/CCDA XML document.

  • Clinical uncertainty markers ("??", "R/O", "Possible") have been
    preserved as documented to maintain diagnostic accuracy.

────────────────────────────────────────────────────────────────


## EXTRACTION RULES

1. **Scan ALL Pages**: Extract from every single page, not just page 1
2. **Combine Related Data**: If thyroid tests span pages 2-3, group together
3. **Preserve Source Attribution**: Add "- Page X" for test results
4. **Handle Duplicates**: If same info twice, include once with both page refs
5. **Chronological Order**: Order by date when dates are present
6. **Professional Tone**: Standard medical documentation language
7. **Completeness**: Include EVERYTHING - don't summarize away details
8. **Expand Abbreviations**: Write out "patient" not "pt" in formal sections
9. **Explain Clinical Reasoning**: In assessment, explain WHY you think each diagnosis

## FORMATTING EXAMPLES

**Lab Results** (table-like format with proper spacing):
```
Thyroid Function Tests (Page 2):
  Test Name                          Value        Status
  ──────────────────────────────────────────────────────
  TSH                                1.85 mIU/L   Normal
  Free T3                            3.3 pg/mL    Normal
  Free T4                            1.1 ng/dL    Normal
  TRAb (TSH Receptor Antibodies)     Negative     Normal
```

**Assessment** (clinical paragraphs, not bullets):
```
1. Possible Psychogenic Polydipsia
   Patient demonstrates excessive fluid intake with marked polyuria
   (~8L/24hr urine output). Urine specific gravity low at 1.008,
   indicating dilute urine. Most endocrine testing unremarkable,
   suggesting primary polydipsia rather than hormonal cause.
```

**Plan** (organized categories with checkboxes):
```
Diagnostic Testing - Ordered:
  ☐ Serial cortisol levels (8 AM and 4 PM)
  ☐ 24-hour urine collection for:
    - Creatinine clearance
    - Free cortisol
```

Generate the complete clinical summary now following this exact structure.
"""


class PDFRenderer:
    """Render MedicalDocument to human-readable PDF using LLM-generated summary"""

    def __init__(self):
        self.config = get_config()
        genai.configure(api_key=self.config.gemini_api_key)
        self.model = genai.GenerativeModel(self.config.structuring_model_name)
        logger.info("PDF renderer initialized (LLM-based)")

    def render(self, document: MedicalDocument, output_path: str) -> None:
        """Render MedicalDocument to PDF

        Args:
            document: MedicalDocument instance
            output_path: Path to save PDF file
        """
        logger.info("Rendering document to PDF (LLM-based)", visits=len(document.visits))

        try:
            # Generate clinical summary using LLM
            if document.raw_ocr_text:
                logger.info("Using raw OCR text for summary generation (preferred)")
                clinical_summary = self._generate_summary_from_ocr(document.raw_ocr_text)
            else:
                logger.info("No raw OCR text available, generating from canonical JSON")
                clinical_summary = self._generate_summary_from_json(document)

            # Create PDF from summary
            self._create_pdf(clinical_summary, output_path, document)

            logger.info("PDF rendering complete (LLM-based)", output_path=output_path)

        except Exception as e:
            logger.error("LLM-based PDF rendering failed", error=str(e))
            raise

    def _generate_summary_from_ocr(self, ocr_text: str) -> str:
        """Generate clinical summary from raw OCR text using LLM"""

        prompt = f"""{CLINICAL_SUMMARY_PROMPT}

---

INPUT DATA (RAW OCR TEXT):

{ocr_text}

---

Generate the complete human-readable clinical summary now. Use the exact format shown above.
"""

        logger.info("Calling LLM for clinical summary generation...")

        response = self.model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.2,  # Slightly creative for better formatting
                top_p=0.95,
                top_k=40,
                max_output_tokens=8192,
            ),
            safety_settings=[
                {
                    "category": HarmCategory.HARM_CATEGORY_HARASSMENT,
                    "threshold": HarmBlockThreshold.BLOCK_NONE,
                },
                {
                    "category": HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    "threshold": HarmBlockThreshold.BLOCK_NONE,
                },
                {
                    "category": HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                    "threshold": HarmBlockThreshold.BLOCK_NONE,
                },
                {
                    "category": HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                    "threshold": HarmBlockThreshold.BLOCK_NONE,
                },
            ],
        )

        summary = response.text.strip()

        # Remove markdown code blocks if present
        if summary.startswith("```"):
            summary = summary.split("\n", 1)[1]
        if summary.endswith("```"):
            summary = summary.rsplit("\n", 1)[0]

        return summary.strip()

    def _generate_summary_from_json(self, document: MedicalDocument) -> str:
        """Fallback: Generate summary from canonical JSON"""
        # Simple text-based summary from JSON if OCR not available
        lines = ["CONTINUITY OF CARE DOCUMENT", "Clinical Summary", ""]

        for visit in document.visits:
            if visit.reason_for_visit:
                lines.append(f"REASON FOR VISIT\n{visit.reason_for_visit}\n")
            if visit.history_of_present_illness:
                lines.append(f"HISTORY\n{visit.history_of_present_illness}\n")
            if visit.assessment:
                lines.append(f"ASSESSMENT\n{visit.assessment}\n")

        return "\n".join(lines)

    def _create_pdf(self, summary_text: str, output_path: str, document: MedicalDocument) -> None:
        """Create PDF from clinical summary text"""

        # Create PDF document
        pdf = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )

        # Setup styles
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#1f77b4'),
            spaceAfter=6,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        styles.add(ParagraphStyle(
            name='CustomHeading',
            parent=styles['Heading2'],
            fontSize=12,
            textColor=colors.HexColor('#2c3e50'),
            spaceBefore=12,
            spaceAfter=6,
            fontName='Helvetica-Bold'
        ))
        styles.add(ParagraphStyle(
            name='CustomBody',
            parent=styles['BodyText'],
            fontSize=10,
            leading=14,
            spaceAfter=8,
            alignment=TA_JUSTIFY
        ))

        # Build content
        story = []

        # Parse and format summary
        lines = summary_text.split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                story.append(Spacer(1, 0.1*inch))
                continue

            # Check if this is a major section header (all caps)
            if line.isupper() and len(line) > 3 and not line.startswith('•'):
                story.append(Paragraph(line, styles['CustomHeading']))
            # Check if title line
            elif 'CONTINUITY OF CARE' in line or 'Specialist Consult' in line:
                story.append(Paragraph(line, styles['CustomTitle']))
            # Regular content
            else:
                story.append(Paragraph(line, styles['CustomBody']))

        # Add footer
        story.append(Spacer(1, 0.3*inch))
        footer_style = ParagraphStyle(
            name='Footer',
            parent=styles['BodyText'],
            fontSize=8,
            textColor=colors.grey,
            alignment=TA_CENTER
        )
        story.append(Paragraph(
            "This document was generated from OCR-processed medical records. "
            "Please verify critical information with original source documents.",
            footer_style
        ))

        # Build PDF
        pdf.build(story)


class RenderError(Exception):
    """Raised when rendering fails"""
    pass
