"""PDF Renderer for Client-Specific Human-Readable Output

Renders canonical JSON to client's exact "Specialist Consult Summary" format.
Matches the client's Practice Fusion-compatible human-readable PDF structure.

CRITICAL: This is a RENDERER ONLY - generates output from canonical JSON.
NO data extraction logic allowed here.
"""

from datetime import datetime
from typing import Dict, Any, List
from io import BytesIO

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER

from ..models.canonical_schema import MedicalDocument
from ..utils.logger import get_logger

logger = get_logger(__name__)


class PDFRenderer:
    """Render canonical JSON to client's Specialist Consult Summary PDF format"""

    def __init__(self):
        logger.info("PDF renderer initialized (Client format)")
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Setup custom paragraph styles matching client's format"""
        # Main title style
        self.styles.add(ParagraphStyle(
            name='MainTitle',
            parent=self.styles['Heading1'],
            fontSize=16,
            textColor=colors.black,
            spaceAfter=4,
            alignment=TA_LEFT,
            fontName='Helvetica-Bold',
        ))

        # Subtitle style
        self.styles.add(ParagraphStyle(
            name='Subtitle',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.black,
            spaceAfter=10,
            alignment=TA_LEFT,
            fontName='Helvetica',
        ))

        # Section heading (bold, left-aligned)
        self.styles.add(ParagraphStyle(
            name='SectionHeading',
            parent=self.styles['Heading3'],
            fontSize=12,
            textColor=colors.black,
            spaceBefore=10,
            spaceAfter=4,
            fontName='Helvetica-Bold',
        ))

        # Normal body text
        self.styles.add(ParagraphStyle(
            name='BodyText',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=colors.black,
            spaceAfter=8,
            leading=14,
        ))

        # Footer note style
        self.styles.add(ParagraphStyle(
            name='FooterNote',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#666666'),
            spaceBefore=20,
            alignment=TA_CENTER,
            fontName='Helvetica-Oblique',
        ))

    def render(self, document: MedicalDocument, output_path: str) -> str:
        """Render MedicalDocument to client's Specialist Consult Summary PDF

        Args:
            document: Validated MedicalDocument instance
            output_path: Path to save PDF file

        Returns:
            Path to saved PDF file
        """
        logger.info("Rendering document to client PDF format", visits=len(document.visits))

        try:
            # Create PDF document with client margins
            pdf = SimpleDocTemplate(
                output_path,
                pagesize=letter,
                rightMargin=0.75*inch,
                leftMargin=0.75*inch,
                topMargin=0.75*inch,
                bottomMargin=0.75*inch,
            )

            # Build content in client's exact format
            story = []

            # Add main header
            self._add_client_header(story, document)

            # Add patient info block
            self._add_patient_info_block(story, document)

            # Process first visit (client format is single-visit oriented)
            if document.visits:
                visit = document.visits[0]

                # Add all clinical sections in client's order
                self._add_section(story, "Reason for Visit", visit.get("reason_for_visit"))
                self._add_section(story, "History of Present Illness", visit.get("history_of_present_illness"))
                self._add_problem_list_client(story, visit.get("problem_list", []))
                self._add_results_client(story, visit)
                self._add_section(story, "Assessment", visit.get("assessment"))
                self._add_plan_client(story, visit.get("plan", []))

            # Add footer note
            self._add_footer_note(story)

            # Build PDF
            pdf.build(story)

            logger.info("PDF rendering complete (client format)", output_path=output_path)
            return output_path

        except Exception as e:
            logger.error("PDF rendering failed", error=str(e))
            raise RenderError(f"Failed to render PDF: {e}")

    def _add_client_header(self, story: List, document: MedicalDocument):
        """Add client's exact header format"""
        # Main title
        story.append(Paragraph("Continuity of Care Document (Human-Readable)", self.styles['MainTitle']))

        # Subtitle - determine specialty from document type or default to general
        specialty = "Medical Consult"
        if document.document_metadata.document_type:
            doc_type = str(document.document_metadata.document_type).lower()
            if "endo" in doc_type:
                specialty = "Endocrinology"
            elif "cardio" in doc_type:
                specialty = "Cardiology"
            # Add more specialty mappings as needed

        story.append(Paragraph(f"Specialist Consult Summary – {specialty}", self.styles['Subtitle']))
        story.append(Spacer(1, 0.15*inch))

    def _add_patient_info_block(self, story: List, document: MedicalDocument):
        """Add patient information block in client's table format"""
        # Get visit date from first visit if available
        visit_date = "N/A"
        if document.visits and document.visits[0].get("visit_date"):
            visit_date = str(document.visits[0]["visit_date"])

        # Patient info table (2 columns, 3 rows)
        patient_data = [
            [
                Paragraph("<b>Patient</b>", self.styles['BodyText']),
                Paragraph(f"<b>Document Date</b> {visit_date}", self.styles['BodyText'])
            ],
            [
                Paragraph(document.document_metadata.patient_name or "{{PATIENT_NAME}}", self.styles['BodyText']),
                ""
            ],
            [
                Paragraph(f"DOB: {document.document_metadata.dob or '{{DOB}}'}", self.styles['BodyText']),
                Paragraph(f"Sex: {document.document_metadata.sex or '{{SEX}}'}", self.styles['BodyText'])
            ],
        ]

        # Add author/organization row if available
        author_org = f"Author / Organization: {document.document_metadata.organization or 'OCR Processing System'}"
        patient_data.append([
            Paragraph(author_org, self.styles['BodyText']),
            ""
        ])

        table = Table(patient_data, colWidths=[3.5*inch, 3*inch])
        table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))

        story.append(table)
        story.append(Spacer(1, 0.2*inch))

    def _add_section(self, story: List, title: str, content: str):
        """Add a standard text section in client format"""
        if not content:
            return

        # Section heading
        story.append(Paragraph(title, self.styles['SectionHeading']))

        # Content
        story.append(Paragraph(content, self.styles['BodyText']))
        story.append(Spacer(1, 0.05*inch))

    def _add_problem_list_client(self, story: List, problems: List[Dict[str, Any]]):
        """Add problem list in client's bullet format"""
        if not problems:
            return

        story.append(Paragraph("Problem List (Summary)", self.styles['SectionHeading']))

        for problem in problems:
            problem_text = f"• {problem.get('problem', '')}"
            if problem.get("status"):
                problem_text += f" ({problem['status']})"
            story.append(Paragraph(problem_text, self.styles['BodyText']))

        story.append(Spacer(1, 0.05*inch))

    def _add_results_client(self, story: List, visit: Dict[str, Any]):
        """Add results section in client's bullet format"""
        results = visit.get("results", [])
        if not results:
            return

        story.append(Paragraph("Results / Relevant Data", self.styles['SectionHeading']))

        # Format results as bullets
        for result in results:
            test_name = result.get("test_name", "Unknown test")
            value = result.get("value", "N/A")
            unit = result.get("unit", "")

            result_text = f"• {test_name}: {value}"
            if unit:
                result_text += f" {unit}"

            # Add reference range if abnormal
            if result.get("abnormal_flag") and result["abnormal_flag"] != "normal":
                result_text += f" ({result['abnormal_flag']})"

            story.append(Paragraph(result_text, self.styles['BodyText']))

        # Add relevant vital signs if present
        vital_signs = visit.get("vital_signs", {})
        if vital_signs:
            for vital_name, vital_data in vital_signs.items():
                if isinstance(vital_data, dict) and vital_data.get("value"):
                    vital_text = f"• {vital_name.replace('_', ' ').title()}: {vital_data['value']}"
                    if vital_data.get("unit"):
                        vital_text += f" {vital_data['unit']}"
                    story.append(Paragraph(vital_text, self.styles['BodyText']))

        story.append(Spacer(1, 0.05*inch))

    def _add_plan_client(self, story: List, plan: List[Dict[str, Any]]):
        """Add plan section in client's bullet format"""
        if not plan:
            return

        story.append(Paragraph("Plan", self.styles['SectionHeading']))

        for item in plan:
            plan_text = f"• {item.get('action', '')}"
            story.append(Paragraph(plan_text, self.styles['BodyText']))

        story.append(Spacer(1, 0.05*inch))

    def _add_footer_note(self, story: List):
        """Add client's exact footer note"""
        footer_text = "Note: Human-readable CCD-style summary for upload/viewing. For standards-based exchange, use CCDA/CCD XML"
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph(footer_text, self.styles['FooterNote']))


class RenderError(Exception):
    """Raised when rendering fails"""
    pass
