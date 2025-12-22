"""XML Renderer for CCD/CCDA-style output

Renders canonical JSON to CCD/CCDA-compatible XML format.
Follows LLM_TECHNICAL_SPEC.md Section 6: XML Output Requirements

CRITICAL: This is a RENDERER ONLY - generates output from canonical JSON.
NO data extraction logic allowed here.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from xml.etree.ElementTree import Element, SubElement, tostring, ElementTree
from xml.dom import minidom
import re

from ..models.canonical_schema import MedicalDocument
from ..utils.logger import get_logger

logger = get_logger(__name__)


class XMLRenderer:
    """Render canonical JSON to CCD/CCDA-style XML"""

    # HL7 namespaces and OIDs
    HL7_NAMESPACE = "urn:hl7-org:v3"
    LOINC_SYSTEM = "2.16.840.1.113883.6.1"
    GENDER_CODE_SYSTEM = "2.16.840.1.113883.5.1"
    ROOT_OID = "2.16.840.1.113883.1.3"

    def __init__(self):
        logger.info("XML renderer initialized")

    def render(self, document: MedicalDocument) -> str:
        """Render MedicalDocument to CCD/CCDA XML string

        Args:
            document: Validated MedicalDocument instance

        Returns:
            XML string (formatted with indentation)
        """
        logger.info("Rendering document to XML", visits=len(document.visits))

        try:
            # Create root element
            root = Element("ClinicalDocument")
            root.set("xmlns", self.HL7_NAMESPACE)

            # Add header elements
            self._add_realm_code(root)
            self._add_type_id(root)
            self._add_document_metadata(root, document)

            # Add patient demographics
            self._add_patient_demographics(root, document)

            # Add structured body
            self._add_structured_body(root, document)

            # Convert to pretty XML string
            xml_string = self._prettify_xml(root)

            logger.info("XML rendering complete", size_bytes=len(xml_string))
            return xml_string

        except Exception as e:
            logger.error("XML rendering failed", error=str(e))
            raise RenderError(f"Failed to render XML: {e}")

    def _add_realm_code(self, root: Element):
        """Add realm code (US)"""
        realm = SubElement(root, "realmCode")
        realm.set("code", "US")

    def _add_type_id(self, root: Element):
        """Add type ID for CCD document"""
        type_id = SubElement(root, "typeId")
        type_id.set("root", self.ROOT_OID)
        type_id.set("extension", "POCD_HD000040")

    def _add_document_metadata(self, root: Element, document: MedicalDocument):
        """Add document-level metadata"""
        # Document ID
        doc_id = SubElement(root, "id")
        doc_id.set("root", "2.16.840.1.113883.19")
        doc_id.set("extension", f"doc_{datetime.now().strftime('%Y%m%d%H%M%S')}")

        # Document title
        title = SubElement(root, "title")
        title.text = "Medical Record Summary (OCR-Processed)"

        # Effective time
        effective_time = SubElement(root, "effectiveTime")
        effective_time.set(
            "value",
            document.document_metadata.processing_metadata.processed_at.strftime("%Y%m%d%H%M%S")
        )

        # Confidentiality code
        confidentiality = SubElement(root, "confidentialityCode")
        confidentiality.set("code", "N")
        confidentiality.set("codeSystem", "2.16.840.1.113883.5.25")

    def _add_patient_demographics(self, root: Element, document: MedicalDocument):
        """Add patient demographics section"""
        record_target = SubElement(root, "recordTarget")
        patient_role = SubElement(record_target, "patientRole")

        # Patient ID
        if document.document_metadata.patient_id:
            patient_id = SubElement(patient_role, "id")
            patient_id.set("extension", str(document.document_metadata.patient_id))
            patient_id.set("root", "2.16.840.1.113883.3.1")
        else:
            patient_id = SubElement(patient_role, "id")
            patient_id.set("nullFlavor", "UNK")

        # Patient details
        patient = SubElement(patient_role, "patient")

        # Name
        if document.document_metadata.patient_name:
            name = SubElement(patient, "name")
            name_parts = self._parse_name(document.document_metadata.patient_name)
            if name_parts.get("given"):
                given = SubElement(name, "given")
                given.text = name_parts["given"]
            if name_parts.get("family"):
                family = SubElement(name, "family")
                family.text = name_parts["family"]
        else:
            name = SubElement(patient, "name")
            name.set("nullFlavor", "UNK")

        # Date of birth
        if document.document_metadata.dob:
            birth_time = SubElement(patient, "birthTime")
            dob_str = document.document_metadata.dob.strftime("%Y%m%d") if hasattr(document.document_metadata.dob, 'strftime') else str(document.document_metadata.dob).replace("-", "")
            birth_time.set("value", dob_str)
        else:
            birth_time = SubElement(patient, "birthTime")
            birth_time.set("nullFlavor", "UNK")

        # Gender
        gender_code = SubElement(patient, "administrativeGenderCode")
        if document.document_metadata.sex:
            sex_map = {"male": "M", "female": "F", "m": "M", "f": "F"}
            code = sex_map.get(document.document_metadata.sex.lower(), "U")
            gender_code.set("code", code)
        else:
            gender_code.set("code", "U")
        gender_code.set("codeSystem", self.GENDER_CODE_SYSTEM)

    def _parse_name(self, full_name: str) -> Dict[str, str]:
        """Parse full name into given and family names

        Args:
            full_name: Full name string

        Returns:
            Dict with 'given' and 'family' keys
        """
        parts = full_name.strip().split()
        if len(parts) == 1:
            return {"given": "", "family": parts[0]}
        elif len(parts) >= 2:
            return {"given": " ".join(parts[:-1]), "family": parts[-1]}
        else:
            return {"given": "", "family": full_name}

    def _add_structured_body(self, root: Element, document: MedicalDocument):
        """Add structured body with all clinical sections"""
        component = SubElement(root, "component")
        structured_body = SubElement(component, "structuredBody")

        # Render each visit as a section
        for visit in document.visits:
            self._add_visit_section(structured_body, visit)

    def _add_visit_section(self, structured_body: Element, visit: Dict[str, Any]):
        """Add a visit as a component section

        Args:
            structured_body: Parent structured body element
            visit: Visit data dictionary
        """
        # Visit container
        visit_component = SubElement(structured_body, "component")
        visit_section = SubElement(visit_component, "section")

        # Section title
        title = SubElement(visit_section, "title")
        visit_date = visit.get("visit_date", "Unknown Date")
        title.text = f"Visit: {visit_date}"

        # Section text
        text_elem = SubElement(visit_section, "text")
        text_content = f"Visit ID: {visit.get('visit_id', 'N/A')}\n"
        text_content += f"Visit Date: {visit_date}\n"
        text_content += f"Encounter Type: {visit.get('encounter_type', 'N/A')}\n"
        text_elem.text = text_content

        # Add clinical subsections
        self._add_reason_for_visit(visit_section, visit)
        self._add_history_of_present_illness(visit_section, visit)
        self._add_problem_list(visit_section, visit)
        self._add_medications(visit_section, visit)
        self._add_vital_signs(visit_section, visit)
        self._add_results(visit_section, visit)
        self._add_assessment(visit_section, visit)
        self._add_plan(visit_section, visit)

    def _add_reason_for_visit(self, parent: Element, visit: Dict[str, Any]):
        """Add reason for visit section"""
        if not visit.get("reason_for_visit"):
            return

        component = SubElement(parent, "component")
        section = SubElement(component, "section")

        code = SubElement(section, "code")
        code.set("code", "29299-5")
        code.set("codeSystem", self.LOINC_SYSTEM)
        code.set("displayName", "Reason for visit")

        title = SubElement(section, "title")
        title.text = "Reason for Visit"

        text = SubElement(section, "text")
        text.text = visit["reason_for_visit"] or "No information available"

    def _add_history_of_present_illness(self, parent: Element, visit: Dict[str, Any]):
        """Add history of present illness section"""
        if not visit.get("history_of_present_illness"):
            return

        component = SubElement(parent, "component")
        section = SubElement(component, "section")

        code = SubElement(section, "code")
        code.set("code", "10164-2")
        code.set("codeSystem", self.LOINC_SYSTEM)
        code.set("displayName", "History of Present Illness")

        title = SubElement(section, "title")
        title.text = "History of Present Illness"

        text = SubElement(section, "text")
        text.text = visit["history_of_present_illness"] or "No information available"

    def _add_problem_list(self, parent: Element, visit: Dict[str, Any]):
        """Add problem list section"""
        problems = visit.get("problem_list", [])
        if not problems:
            return

        component = SubElement(parent, "component")
        section = SubElement(component, "section")

        code = SubElement(section, "code")
        code.set("code", "11450-4")
        code.set("codeSystem", self.LOINC_SYSTEM)
        code.set("displayName", "Problem List")

        title = SubElement(section, "title")
        title.text = "Problem List"

        text = SubElement(section, "text")
        list_elem = SubElement(text, "list")

        for problem in problems:
            item = SubElement(list_elem, "item")
            problem_text = problem.get("problem", "")
            if problem.get("icd10_code"):
                problem_text += f" ({problem['icd10_code']})"
            if problem.get("source_page"):
                problem_text += f" [Page {problem['source_page']}]"
            item.text = problem_text

    def _add_medications(self, parent: Element, visit: Dict[str, Any]):
        """Add medications section"""
        medications = visit.get("medications", [])
        if not medications:
            return

        component = SubElement(parent, "component")
        section = SubElement(component, "section")

        code = SubElement(section, "code")
        code.set("code", "10160-0")
        code.set("codeSystem", self.LOINC_SYSTEM)
        code.set("displayName", "Medication History")

        title = SubElement(section, "title")
        title.text = "Medications"

        text = SubElement(section, "text")
        table = SubElement(text, "table")

        # Table header
        thead = SubElement(table, "thead")
        tr = SubElement(thead, "tr")
        for header in ["Medication", "Dose", "Frequency", "Route", "Source Page"]:
            th = SubElement(tr, "th")
            th.text = header

        # Table body
        tbody = SubElement(table, "tbody")
        for med in medications:
            tr = SubElement(tbody, "tr")

            td_name = SubElement(tr, "td")
            td_name.text = med.get("name", "")

            td_dose = SubElement(tr, "td")
            td_dose.text = med.get("dose", "") or "N/A"

            td_freq = SubElement(tr, "td")
            td_freq.text = med.get("frequency", "") or "N/A"

            td_route = SubElement(tr, "td")
            td_route.text = med.get("route", "") or "N/A"

            td_page = SubElement(tr, "td")
            td_page.text = str(med.get("source_page", "")) or "N/A"

    def _add_vital_signs(self, parent: Element, visit: Dict[str, Any]):
        """Add vital signs section"""
        vitals = visit.get("vital_signs", {})
        if not vitals or not any(v.get("value") for v in vitals.values() if isinstance(v, dict)):
            return

        component = SubElement(parent, "component")
        section = SubElement(component, "section")

        code = SubElement(section, "code")
        code.set("code", "8716-3")
        code.set("codeSystem", self.LOINC_SYSTEM)
        code.set("displayName", "Vital Signs")

        title = SubElement(section, "title")
        title.text = "Vital Signs"

        text = SubElement(section, "text")
        list_elem = SubElement(text, "list")

        for vital_name, vital_data in vitals.items():
            if isinstance(vital_data, dict) and vital_data.get("value"):
                item = SubElement(list_elem, "item")
                value = vital_data["value"]
                unit = vital_data.get("unit", "")
                item.text = f"{vital_name}: {value} {unit}".strip()

    def _add_results(self, parent: Element, visit: Dict[str, Any]):
        """Add lab results section"""
        results = visit.get("results", [])
        if not results:
            return

        component = SubElement(parent, "component")
        section = SubElement(component, "section")

        code = SubElement(section, "code")
        code.set("code", "30954-2")
        code.set("codeSystem", self.LOINC_SYSTEM)
        code.set("displayName", "Relevant diagnostic tests/laboratory data")

        title = SubElement(section, "title")
        title.text = "Results"

        text = SubElement(section, "text")
        table = SubElement(text, "table")

        # Table header
        thead = SubElement(table, "thead")
        tr = SubElement(thead, "tr")
        for header in ["Test", "Value", "Unit", "Reference Range", "Flag", "Source Page"]:
            th = SubElement(tr, "th")
            th.text = header

        # Table body
        tbody = SubElement(table, "tbody")
        for result in results:
            tr = SubElement(tbody, "tr")

            td_test = SubElement(tr, "td")
            td_test.text = result.get("test_name", "")

            td_value = SubElement(tr, "td")
            td_value.text = str(result.get("value", "")) or "N/A"

            td_unit = SubElement(tr, "td")
            td_unit.text = result.get("unit", "") or "N/A"

            td_ref = SubElement(tr, "td")
            td_ref.text = result.get("reference_range", "") or "N/A"

            td_flag = SubElement(tr, "td")
            td_flag.text = result.get("abnormal_flag", "") or "normal"

            td_page = SubElement(tr, "td")
            td_page.text = str(result.get("source_page", "")) or "N/A"

    def _add_assessment(self, parent: Element, visit: Dict[str, Any]):
        """Add assessment section"""
        if not visit.get("assessment"):
            return

        component = SubElement(parent, "component")
        section = SubElement(component, "section")

        code = SubElement(section, "code")
        code.set("code", "51848-0")
        code.set("codeSystem", self.LOINC_SYSTEM)
        code.set("displayName", "Assessment")

        title = SubElement(section, "title")
        title.text = "Assessment"

        text = SubElement(section, "text")
        text.text = visit["assessment"] or "No information available"

    def _add_plan(self, parent: Element, visit: Dict[str, Any]):
        """Add plan of care section"""
        plan = visit.get("plan", [])
        if not plan:
            return

        component = SubElement(parent, "component")
        section = SubElement(component, "section")

        code = SubElement(section, "code")
        code.set("code", "18776-5")
        code.set("codeSystem", self.LOINC_SYSTEM)
        code.set("displayName", "Plan of Care")

        title = SubElement(section, "title")
        title.text = "Plan"

        text = SubElement(section, "text")
        list_elem = SubElement(text, "list")

        for plan_item in plan:
            item = SubElement(list_elem, "item")
            action_text = plan_item.get("action", "")
            if plan_item.get("category"):
                action_text += f" ({plan_item['category']})"
            if plan_item.get("source_page"):
                action_text += f" [Page {plan_item['source_page']}]"
            item.text = action_text

    def _prettify_xml(self, elem: Element) -> str:
        """Convert XML element to pretty-printed string

        Args:
            elem: XML Element

        Returns:
            Pretty-printed XML string with proper indentation
        """
        rough_string = tostring(elem, encoding='utf-8')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ", encoding="UTF-8").decode('utf-8')


class RenderError(Exception):
    """Raised when rendering fails"""
    pass
