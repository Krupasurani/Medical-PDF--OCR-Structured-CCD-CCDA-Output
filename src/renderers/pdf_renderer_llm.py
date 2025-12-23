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

You are generating a comprehensive, professional human-readable clinical summary from medical OCR text.

**INPUT**: Raw OCR text from medical documents (handwritten + printed notes across multiple pages)

## CRITICAL REQUIREMENTS

1. **Extract ALL clinical information** from ALL pages
2. **Organize chronologically** when dates are available
3. **Preserve clinical uncertainty** - keep "??", "R/O", "Poss.", "[UNCLEAR]" exactly as written
4. **Use professional medical language** - clear, concise, clinical style
5. **Group related information** - combine scattered data into coherent sections
6. **Return ONLY formatted text** - no explanations, no markdown headers (use plain text with bullets)

---

## OUTPUT FORMAT

Generate a professional clinical summary in this EXACT format:

```
CONTINUITY OF CARE DOCUMENT
Specialist Consult Summary - [Specialty]

PATIENT INFORMATION
Name: [from OCR or "Not recorded"]
Date of Birth: [from OCR or "Not recorded"]
Sex: [from OCR or "Not recorded"]
Document Date: [from OCR or "Not recorded"]
Provider: [from OCR or "Not recorded"]

REASON FOR VISIT
[Extract chief complaint and reason for visit from OCR text. Combine all mentions across pages.]

HISTORY OF PRESENT ILLNESS
[Comprehensive HPI combining information from all pages. Include:
- Onset and duration of symptoms
- Patient's description of symptoms
- Relevant timeline
- Associated symptoms
- Aggravating/alleviating factors
Preserve exact wording from OCR where important.]

PAST MEDICAL HISTORY
[List all mentioned past medical conditions, surgeries, hospitalizations]
• [Condition 1]
• [Condition 2]

MEDICATIONS
[List all medications mentioned across ALL pages with dose/frequency]
• [Medication 1] - [dose] - [frequency]
• [Medication 2] - [dose] - [frequency]

ALLERGIES
[List all allergies mentioned, or "No known allergies documented" or "Not documented"]

VITAL SIGNS
[If present in OCR]
• Blood Pressure: [value]
• Heart Rate: [value]
• Temperature: [value]
• Respiratory Rate: [value]
• Oxygen Saturation: [value]

PROBLEM LIST / DIAGNOSES
[List ALL problems/diagnoses mentioned across ALL pages. Preserve uncertainty markers.]
• ?? [Problem with uncertainty marker]
• R/O [Rule-out diagnosis]
• [Confirmed diagnosis]

LABORATORY RESULTS AND DIAGNOSTIC TESTS
[Comprehensive list of ALL test results from ALL pages, organized by category]

Laboratory Tests:
• [Test name]: [value] [unit] [flag if abnormal] - [Page X]
• [Test name]: [value] [unit] - [Page Y]

Imaging/Other Studies:
• [Study name]: [findings] - [Page X]

ASSESSMENT AND IMPRESSION
[Clinician's assessment combining all impressions from all pages. Group by page/visit if multiple assessments present:]

Page [X] Assessment:
[Clinical impression from page X]

Page [Y] Assessment:
[Clinical impression from page Y]

PLAN OF CARE
[Comprehensive treatment plan combining ALL plan items from ALL pages. Group logically:]

Medications/Treatments:
• [Specific medication changes or treatments]

Diagnostic Studies:
• [Ordered tests, labs, imaging]

Follow-up:
• [Return visit instructions]
• [Monitoring instructions]

Patient Education:
• [Lifestyle modifications]
• [Patient instructions]

```

---

## EXTRACTION RULES

1. **Scan ALL Pages**: Don't stop after page 1 - extract from every page
2. **Combine Related Data**: If TSH is on page 2 and FT3/FT4 on page 3, list together
3. **Preserve Source Attribution**: Add "- Page X" for test results to show source
4. **Handle Duplicates**: If same info appears twice, include once with both page refs
5. **Chronological Order**: If dates present, order by date (oldest → newest)
6. **Professional Tone**: Use standard medical documentation language
7. **Completeness**: Include EVERYTHING - don't summarize away important details

---

## EXAMPLES

**Uncertainty Markers** (preserve these):
- ?? Psychogenic polydipsia
- R/O Pheochromocytoma
- Poss. Reactive Hypoglycemia

**Lab Results** (include units and page refs):
- TSH: 1.85 mIU/L - Page 2
- FT3: 3.3 pg/mL - Page 2
- Cortisol: 52.9 (ok?) - Page 1

**Multiple Assessments** (combine all):
Page 1 Assessment: ?? Psychogenic polydipsia. Poss. Reactive Hypoglycemia w Anxiety / MNS
Page 2 Assessment: R/O Pheochromocytoma vs MEA. MNCT / R/O D.I vs. Polydypsia
Page 5 Assessment: Hx? Hypoglycemia c Anxiety. Hx. GERD. MNG (Hashimoto)

---

## OUTPUT INSTRUCTIONS

1. Generate the complete clinical summary following the format above
2. Use plain text with bullet points (•) for lists
3. NO markdown syntax (no #, **, `, etc.)
4. Include ALL information from ALL pages
5. Be comprehensive but organized
6. Preserve medical abbreviations and terminology as written in OCR

Generate the clinical summary now.
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
