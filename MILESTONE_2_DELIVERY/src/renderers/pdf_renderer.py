"""PDF Renderer for human-readable output

Renders canonical JSON to professional PDF format.
Follows LLM_TECHNICAL_SPEC.md Section 7: Human-Readable Output

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
    """Render canonical JSON to professional PDF document"""

    def __init__(self):
        logger.info("PDF renderer initialized")
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        # Header style
        self.styles.add(ParagraphStyle(
            name='CustomHeader',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=12,
            alignment=TA_CENTER,
        ))

        # Section heading
        self.styles.add(ParagraphStyle(
            name='SectionHeading',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#2c3e50'),
            spaceBefore=12,
            spaceAfter=6,
            borderWidth=1,
            borderColor=colors.HexColor('#3498db'),
            borderPadding=4,
        ))

        # Warning style
        self.styles.add(ParagraphStyle(
            name='Warning',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#e74c3c'),
            leftIndent=20,
            spaceBefore=6,
        ))

        # Source info style
        self.styles.add(ParagraphStyle(
            name='SourceInfo',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#7f8c8d'),
            leftIndent=20,
        ))

    def render(self, document: MedicalDocument, output_path: str) -> str:
        """Render MedicalDocument to PDF file

        Args:
            document: Validated MedicalDocument instance
            output_path: Path to save PDF file

        Returns:
            Path to saved PDF file
        """
        logger.info("Rendering document to PDF", visits=len(document.visits))

        try:
            # Create PDF document
            pdf = SimpleDocTemplate(
                output_path,
                pagesize=letter,
                rightMargin=1*inch,
                leftMargin=1*inch,
                topMargin=1*inch,
                bottomMargin=1*inch,
            )

            # Build content
            story = []

            # Add header
            self._add_header(story, document)

            # Add disclaimer
            self._add_disclaimer(story)

            # Add patient demographics
            self._add_patient_demographics(story, document)

            # Add each visit
            for i, visit in enumerate(document.visits):
                if i > 0:
                    story.append(PageBreak())
                self._add_visit(story, visit, i + 1)

            # Add data quality section
            self._add_data_quality(story, document)

            # Build PDF
            pdf.build(story)

            logger.info("PDF rendering complete", output_path=output_path)
            return output_path

        except Exception as e:
            logger.error("PDF rendering failed", error=str(e))
            raise RenderError(f"Failed to render PDF: {e}")

    def _add_header(self, story: List, document: MedicalDocument):
        """Add document header"""
        story.append(Paragraph("MEDICAL RECORD SUMMARY", self.styles['CustomHeader']))
        story.append(Spacer(1, 0.2*inch))

        # Metadata table
        metadata = [
            ["Patient:", document.document_metadata.patient_name or "Unknown"],
            ["DOB:", str(document.document_metadata.dob) if document.document_metadata.dob else "Unknown"],
            ["Sex:", document.document_metadata.sex or "Unknown"],
            ["Document Type:", document.document_metadata.document_type or "Mixed"],
            ["Generated:", document.processed_at.strftime("%Y-%m-%d %H:%M:%S")],
            ["Source:", "OCR-processed medical record"],
        ]

        table = Table(metadata, colWidths=[1.5*inch, 4.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
        ]))

        story.append(table)
        story.append(Spacer(1, 0.3*inch))

    def _add_disclaimer(self, story: List):
        """Add important disclaimer"""
        disclaimer_text = """<b>IMPORTANT:</b> This document was generated from OCR-processed scanned medical records.
All information should be reviewed by qualified healthcare professionals. Do not use as the sole source
of patient information for clinical decision-making. Always refer to original source documents for critical decisions."""

        story.append(Paragraph(disclaimer_text, self.styles['Warning']))
        story.append(Spacer(1, 0.2*inch))

    def _add_patient_demographics(self, story: List, document: MedicalDocument):
        """Add patient demographics section"""
        story.append(Paragraph("PATIENT DEMOGRAPHICS", self.styles['SectionHeading']))

        demo_data = []
        if document.document_metadata.patient_name:
            demo_data.append(["Name:", document.document_metadata.patient_name])
        if document.document_metadata.patient_id:
            demo_data.append(["Patient ID:", str(document.document_metadata.patient_id)])
        if document.document_metadata.dob:
            demo_data.append(["Date of Birth:", str(document.document_metadata.dob)])
        if document.document_metadata.sex:
            demo_data.append(["Sex:", document.document_metadata.sex])

        if demo_data:
            table = Table(demo_data, colWidths=[1.5*inch, 4.5*inch])
            table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ]))
            story.append(table)
        else:
            story.append(Paragraph("No patient demographics available", self.styles['Normal']))

        story.append(Spacer(1, 0.2*inch))

    def _add_visit(self, story: List, visit: Dict[str, Any], visit_number: int):
        """Add a visit section"""
        # Visit header
        visit_title = f"VISIT {visit_number}: {visit.get('visit_date', 'Unknown Date')}"
        story.append(Paragraph(visit_title, self.styles['SectionHeading']))

        # Visit metadata
        meta_data = [
            ["Visit ID:", visit.get("visit_id", "N/A")],
            ["Visit Date:", visit.get("visit_date", "N/A")],
            ["Encounter Type:", visit.get("encounter_type", "N/A")],
            ["Source Pages:", ", ".join(map(str, visit.get("raw_source_pages", [])))],
        ]

        table = Table(meta_data, colWidths=[1.5*inch, 4.5*inch])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        story.append(table)
        story.append(Spacer(1, 0.15*inch))

        # Clinical sections
        self._add_text_section(story, "Reason for Visit", visit.get("reason_for_visit"))
        self._add_text_section(story, "History of Present Illness", visit.get("history_of_present_illness"))
        self._add_medications_section(story, visit.get("medications", []))
        self._add_vital_signs_section(story, visit.get("vital_signs", {}))
        self._add_problem_list_section(story, visit.get("problem_list", []))
        self._add_results_section(story, visit.get("results", []))
        self._add_text_section(story, "Assessment", visit.get("assessment"))
        self._add_plan_section(story, visit.get("plan", []))

        # Review flags
        if visit.get("manual_review_required"):
            story.append(Spacer(1, 0.1*inch))
            warning = f"⚠ MANUAL REVIEW REQUIRED: {', '.join(visit.get('review_reasons', []))}"
            story.append(Paragraph(warning, self.styles['Warning']))

    def _add_text_section(self, story: List, title: str, content: str):
        """Add a simple text section"""
        if not content:
            return

        story.append(Paragraph(f"<b>{title.upper()}</b>", self.styles['Heading3']))
        story.append(Spacer(1, 0.05*inch))
        story.append(Paragraph(content, self.styles['Normal']))
        story.append(Spacer(1, 0.1*inch))

    def _add_medications_section(self, story: List, medications: List[Dict[str, Any]]):
        """Add medications section with table"""
        if not medications:
            return

        story.append(Paragraph("<b>MEDICATIONS</b>", self.styles['Heading3']))
        story.append(Spacer(1, 0.05*inch))

        # Table data
        data = [["Medication", "Dose", "Frequency", "Route", "Page"]]
        for med in medications:
            data.append([
                med.get("name", ""),
                med.get("dose", "") or "N/A",
                med.get("frequency", "") or "N/A",
                med.get("route", "") or "N/A",
                str(med.get("source_page", "")) or "N/A",
            ])

        table = Table(data, colWidths=[2*inch, 1*inch, 1*inch, 0.8*inch, 0.7*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ]))

        story.append(table)
        story.append(Spacer(1, 0.1*inch))

    def _add_vital_signs_section(self, story: List, vital_signs: Dict[str, Any]):
        """Add vital signs section"""
        if not vital_signs or not any(v.get("value") for v in vital_signs.values() if isinstance(v, dict)):
            return

        story.append(Paragraph("<b>VITAL SIGNS</b>", self.styles['Heading3']))
        story.append(Spacer(1, 0.05*inch))

        data = [["Vital Sign", "Value", "Unit"]]
        for vital_name, vital_data in vital_signs.items():
            if isinstance(vital_data, dict) and vital_data.get("value"):
                data.append([
                    vital_name.replace("_", " ").title(),
                    str(vital_data["value"]),
                    vital_data.get("unit", ""),
                ])

        if len(data) > 1:
            table = Table(data, colWidths=[2*inch, 1.5*inch, 1*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2ecc71')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ]))
            story.append(table)

        story.append(Spacer(1, 0.1*inch))

    def _add_problem_list_section(self, story: List, problems: List[Dict[str, Any]]):
        """Add problem list section"""
        if not problems:
            return

        story.append(Paragraph("<b>PROBLEM LIST</b>", self.styles['Heading3']))
        story.append(Spacer(1, 0.05*inch))

        for problem in problems:
            problem_text = f"• {problem.get('problem', '')}"
            if problem.get("icd10_code"):
                problem_text += f" (ICD-10: {problem['icd10_code']})"
            if problem.get("status"):
                problem_text += f" - {problem['status']}"
            if problem.get("source_page"):
                problem_text += f" [Page {problem['source_page']}]"

            story.append(Paragraph(problem_text, self.styles['Normal']))

        story.append(Spacer(1, 0.1*inch))

    def _add_results_section(self, story: List, results: List[Dict[str, Any]]):
        """Add lab results section with table"""
        if not results:
            return

        story.append(Paragraph("<b>LAB RESULTS</b>", self.styles['Heading3']))
        story.append(Spacer(1, 0.05*inch))

        data = [["Test", "Value", "Unit", "Reference Range", "Flag", "Page"]]
        for result in results:
            data.append([
                result.get("test_name", ""),
                str(result.get("value", "")) or "N/A",
                result.get("unit", "") or "N/A",
                result.get("reference_range", "") or "N/A",
                result.get("abnormal_flag", "") or "normal",
                str(result.get("source_page", "")) or "N/A",
            ])

        table = Table(data, colWidths=[1.5*inch, 0.8*inch, 0.7*inch, 1.2*inch, 0.7*inch, 0.6*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e74c3c')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ]))

        story.append(table)
        story.append(Spacer(1, 0.1*inch))

    def _add_plan_section(self, story: List, plan: List[Dict[str, Any]]):
        """Add plan of care section"""
        if not plan:
            return

        story.append(Paragraph("<b>PLAN OF CARE</b>", self.styles['Heading3']))
        story.append(Spacer(1, 0.05*inch))

        for item in plan:
            plan_text = f"• {item.get('action', '')}"
            if item.get("category"):
                plan_text += f" ({item['category']})"
            if item.get("source_page"):
                plan_text += f" [Page {item['source_page']}]"

            story.append(Paragraph(plan_text, self.styles['Normal']))

        story.append(Spacer(1, 0.1*inch))

    def _add_data_quality(self, story: List, document: MedicalDocument):
        """Add data quality notes"""
        story.append(PageBreak())
        story.append(Paragraph("DATA QUALITY NOTES", self.styles['SectionHeading']))
        story.append(Spacer(1, 0.1*inch))

        # Quality metrics
        quality_data = [
            ["OCR Confidence (Average):", f"{document.ocr_confidence_avg * 100:.1f}%"],
            ["Pages Processed:", str(document.page_count)],
            ["Processing Duration:", f"{document.processing_duration_ms / 1000:.2f} seconds" if document.processing_duration_ms else "N/A"],
        ]

        table = Table(quality_data, colWidths=[2*inch, 3*inch])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(table)
        story.append(Spacer(1, 0.15*inch))

        # Warnings
        if document.data_quality.unclear_sections:
            story.append(Paragraph("<b>⚠ Sections with Reduced Confidence:</b>", self.styles['Warning']))
            for unclear in document.data_quality.unclear_sections:
                warning_text = f"• {unclear.get('section', 'Unknown')} (Page {unclear.get('page', 'N/A')}): {unclear.get('reason', '')}"
                story.append(Paragraph(warning_text, self.styles['Normal']))


class RenderError(Exception):
    """Raised when rendering fails"""
    pass
