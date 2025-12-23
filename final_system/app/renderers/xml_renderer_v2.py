"""XML Renderer for Practice Fusion-Compatible CDA R2.1 Output

Renders canonical JSON to Practice Fusion-optimized CCD/C-CDA XML format.
Matches client's exact XML structure with proper template IDs, SNOMED/LOINC codes.

CRITICAL: This is a RENDERER ONLY - generates output from canonical JSON.
NO data extraction logic allowed here.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
import uuid

from ..models.canonical_schema import MedicalDocument
from ..utils.logger import get_logger

logger = get_logger(__name__)


class XMLRenderer:
    """Render canonical JSON to Practice Fusion-compatible CCD/C-CDA XML"""

    # HL7 namespaces and OIDs
    HL7_NAMESPACE = "urn:hl7-org:v3"
    XSI_NAMESPACE = "http://www.w3.org/2001/XMLSchema-instance"
    SDTC_NAMESPACE = "urn:hl7-org:sdtc"

    # Code systems
    LOINC_SYSTEM = "2.16.840.1.113883.6.1"
    SNOMED_SYSTEM = "2.16.840.1.113883.6.96"
    GENDER_CODE_SYSTEM = "2.16.840.1.113883.5.1"

    # Template IDs (Practice Fusion CDA R2.1)
    CCD_TEMPLATE = "2.16.840.1.113883.10.20.22.1.1"
    REASON_VISIT_TEMPLATE = "2.16.840.1.113883.10.20.22.2.12"
    PROBLEM_SECTION_TEMPLATE = "2.16.840.1.113883.10.20.22.2.5.1"
    PROBLEM_CONCERN_ACT_TEMPLATE = "2.16.840.1.113883.10.20.22.4.3"
    PROBLEM_OBSERVATION_TEMPLATE = "2.16.840.1.113883.10.20.22.4.4"
    RESULTS_SECTION_TEMPLATE = "2.16.840.1.113883.10.20.22.2.3.1"
    RESULTS_ORGANIZER_TEMPLATE = "2.16.840.1.113883.10.20.22.4.1"
    RESULT_OBSERVATION_TEMPLATE = "2.16.840.1.113883.10.20.22.4.2"

    # Common SNOMED codes for problems
    SNOMED_CODES = {
        "polyuria": "284121005",
        "polydipsia": "267064002",
        "anxiety": "48694002",
        "hypoglycemia": "302866003",
        "diabetes insipidus": "15771004",
    }

    # Common LOINC codes for lab tests
    LOINC_CODES = {
        "glucose": "2345-7",  # Glucose [Mass/volume] in Serum or Plasma
        "24-hour urine volume": "3167-4",  # Volume of 24 hour Urine
        "urine specific gravity": "2965-2",  # Specific gravity of Urine
    }

    def __init__(self):
        logger.info("XML renderer initialized (Practice Fusion CDA R2.1)")

    def render(self, document: MedicalDocument) -> str:
        """Render MedicalDocument to Practice Fusion CCD/C-CDA XML string

        Args:
            document: Validated MedicalDocument instance

        Returns:
            XML string (formatted with indentation)
        """
        logger.info("Rendering document to Practice Fusion XML", visits=len(document.visits))

        try:
            # Create root element with namespaces
            root = Element("ClinicalDocument")
            root.set("xmlns", self.HL7_NAMESPACE)
            root.set(f"xmlns:xsi", self.XSI_NAMESPACE)
            root.set(f"xmlns:sdtc", self.SDTC_NAMESPACE)

            # Add document header
            self._add_document_header(root, document)

            # Add patient
            self._add_patient(root, document)

            # Add author
            self._add_author(root, document)

            # Add custodian
            self._add_custodian(root, document)

            # Add encounter
            self._add_encounter(root, document)

            # Add structured body
            self._add_structured_body(root, document)

            # Convert to pretty XML string
            xml_string = self._prettify_xml(root)

            logger.info("XML rendering complete", size_bytes=len(xml_string))
            return xml_string

        except Exception as e:
            logger.error("XML rendering failed", error=str(e))
            raise RenderError(f"Failed to render XML: {e}")

    def _add_document_header(self, root: Element, document: MedicalDocument):
        """Add document header with template IDs and metadata"""
        # Type ID
        type_id = SubElement(root, "typeId")
        type_id.set("root", "2.16.840.1.113883.1.3")
        type_id.set("extension", "POCD_HD000040")

        # Template ID - CCD
        template_id = SubElement(root, "templateId")
        template_id.set("root", self.CCD_TEMPLATE)

        # Document ID
        doc_id = SubElement(root, "id")
        doc_id.set("root", "2.16.840.1.113883.19")
        doc_id.set("extension", f"doc_{uuid.uuid4().hex[:16]}")

        # Code - Summarization of Episode Note
        code = SubElement(root, "code")
        code.set("code", "34133-9")
        code.set("codeSystem", self.LOINC_SYSTEM)
        code.set("displayName", "Summarization of Episode Note")

        # Title
        title = SubElement(root, "title")
        title.text = "Continuity of Care Document (CCD) - Specialist Consult Summary"

        # Effective time
        effective_time = SubElement(root, "effectiveTime")
        effective_time.set("value", document.processed_at.strftime("%Y%m%d%H%M%S"))

        # Confidentiality code
        confidentiality = SubElement(root, "confidentialityCode")
        confidentiality.set("code", "N")
        confidentiality.set("codeSystem", "2.16.840.1.113883.5.25")

        # Language code
        language = SubElement(root, "languageCode")
        language.set("code", "en-US")

    def _add_patient(self, root: Element, document: MedicalDocument):
        """Add patient demographics section"""
        record_target = SubElement(root, "recordTarget")
        patient_role = SubElement(record_target, "patientRole")

        # Patient ID
        patient_id = SubElement(patient_role, "id")
        if document.document_metadata.patient_id:
            patient_id.set("root", "2.16.840.1.113883.3.1")
            patient_id.set("extension", str(document.document_metadata.patient_id))
        else:
            patient_id.set("nullFlavor", "UNK")

        # Address (placeholder - OCR doesn't typically extract this)
        addr = SubElement(patient_role, "addr")
        addr.set("use", "HP")
        addr.set("nullFlavor", "UNK")

        # Telecom (placeholder)
        telecom = SubElement(patient_role, "telecom")
        telecom.set("nullFlavor", "UNK")

        # Patient details
        patient = SubElement(patient_role, "patient")

        # Name
        name = SubElement(patient, "name")
        if document.document_metadata.patient_name:
            name_parts = self._parse_name(document.document_metadata.patient_name)
            if name_parts.get("given"):
                given = SubElement(name, "given")
                given.text = name_parts["given"]
            if name_parts.get("family"):
                family = SubElement(name, "family")
                family.text = name_parts["family"]
        else:
            name.set("nullFlavor", "UNK")

        # Gender
        gender_code = SubElement(patient, "administrativeGenderCode")
        if document.document_metadata.sex:
            sex_map = {"male": "M", "female": "F", "m": "M", "f": "F"}
            code = sex_map.get(str(document.document_metadata.sex).lower(), "U")
            gender_code.set("code", code)
        else:
            gender_code.set("code", "U")
        gender_code.set("codeSystem", self.GENDER_CODE_SYSTEM)

        # Birth time
        birth_time = SubElement(patient, "birthTime")
        if document.document_metadata.dob:
            dob_str = document.document_metadata.dob.strftime("%Y%m%d") if hasattr(document.document_metadata.dob, 'strftime') else str(document.document_metadata.dob).replace("-", "")
            birth_time.set("value", dob_str)
        else:
            birth_time.set("nullFlavor", "UNK")

    def _add_author(self, root: Element, document: MedicalDocument):
        """Add author section (OCR processor)"""
        author = SubElement(root, "author")

        # Time
        time = SubElement(author, "time")
        time.set("value", document.processed_at.strftime("%Y%m%d%H%M%S"))

        # Assigned author
        assigned_author = SubElement(author, "assignedAuthor")

        # ID
        author_id = SubElement(assigned_author, "id")
        author_id.set("root", "2.16.840.1.113883.19.5")
        author_id.set("extension", "OCR_SYSTEM")

        # Address (nullFlavor for automated system)
        addr = SubElement(assigned_author, "addr")
        addr.set("nullFlavor", "UNK")

        # Telecom
        telecom = SubElement(assigned_author, "telecom")
        telecom.set("nullFlavor", "UNK")

        # Assigned person
        assigned_person = SubElement(assigned_author, "assignedPerson")
        name = SubElement(assigned_person, "name")
        name.text = "Medical PDF OCR System"

        # Represented organization
        if document.document_metadata.organization:
            rep_org = SubElement(assigned_author, "representedOrganization")
            org_id = SubElement(rep_org, "id")
            org_id.set("nullFlavor", "UNK")
            org_name = SubElement(rep_org, "name")
            org_name.text = document.document_metadata.organization

    def _add_custodian(self, root: Element, document: MedicalDocument):
        """Add custodian section"""
        custodian = SubElement(root, "custodian")
        assigned_custodian = SubElement(custodian, "assignedCustodian")
        rep_custodian_org = SubElement(assigned_custodian, "representedCustodianOrganization")

        # ID
        custodian_id = SubElement(rep_custodian_org, "id")
        custodian_id.set("root", "2.16.840.1.113883.19.5")
        custodian_id.set("extension", "CUSTODIAN")

        # Name
        custodian_name = SubElement(rep_custodian_org, "name")
        custodian_name.text = document.document_metadata.organization or "Medical Records Department"

    def _add_encounter(self, root: Element, document: MedicalDocument):
        """Add encompassing encounter"""
        component_of = SubElement(root, "componentOf")
        encompassing_encounter = SubElement(component_of, "encompassingEncounter")

        # Encounter ID
        encounter_id = SubElement(encompassing_encounter, "id")
        # Use first visit's ID if available
        if document.visits:
            encounter_id.set("root", "2.16.840.1.113883.19")
            encounter_id.set("extension", document.visits[0].get("visit_id", "encounter_001"))
        else:
            encounter_id.set("nullFlavor", "UNK")

        # Effective time
        effective_time = SubElement(encompassing_encounter, "effectiveTime")
        if document.visits and document.visits[0].get("visit_date"):
            visit_date = document.visits[0]["visit_date"]
            if isinstance(visit_date, str):
                # Try to parse date string
                date_value = visit_date.replace("-", "")
            else:
                date_value = visit_date.strftime("%Y%m%d") if hasattr(visit_date, 'strftime') else "UNK"
            effective_time.set("value", date_value)
        else:
            effective_time.set("nullFlavor", "UNK")

    def _add_structured_body(self, root: Element, document: MedicalDocument):
        """Add structured body with all clinical sections"""
        component = SubElement(root, "component")
        structured_body = SubElement(component, "structuredBody")

        # Process first visit (for now)
        if document.visits:
            visit = document.visits[0]

            # Reason for visit
            self._add_reason_for_visit_section(structured_body, visit)

            # History of present illness
            self._add_hpi_section(structured_body, visit)

            # Problem list
            self._add_problem_section(structured_body, visit)

            # Results
            self._add_results_section(structured_body, visit)

            # Assessment
            self._add_assessment_section(structured_body, visit)

            # Plan
            self._add_plan_section(structured_body, visit)

    def _add_reason_for_visit_section(self, structured_body: Element, visit: Dict[str, Any]):
        """Add reason for visit section"""
        if not visit.get("reason_for_visit"):
            return

        component = SubElement(structured_body, "component")
        section = SubElement(component, "section")

        # Template ID
        template_id = SubElement(section, "templateId")
        template_id.set("root", self.REASON_VISIT_TEMPLATE)

        # Code
        code = SubElement(section, "code")
        code.set("code", "29299-5")
        code.set("codeSystem", self.LOINC_SYSTEM)
        code.set("displayName", "Reason for visit")

        # Title
        title = SubElement(section, "title")
        title.text = "Reason for Visit"

        # Text
        text = SubElement(section, "text")
        paragraph = SubElement(text, "paragraph")
        paragraph.text = visit["reason_for_visit"]

    def _add_hpi_section(self, structured_body: Element, visit: Dict[str, Any]):
        """Add history of present illness section"""
        if not visit.get("history_of_present_illness"):
            return

        component = SubElement(structured_body, "component")
        section = SubElement(component, "section")

        # Code
        code = SubElement(section, "code")
        code.set("code", "10164-2")
        code.set("codeSystem", self.LOINC_SYSTEM)
        code.set("displayName", "History of Present Illness")

        # Title
        title = SubElement(section, "title")
        title.text = "History of Present Illness"

        # Text
        text = SubElement(section, "text")
        paragraph = SubElement(text, "paragraph")
        paragraph.text = visit["history_of_present_illness"]

    def _add_problem_section(self, structured_body: Element, visit: Dict[str, Any]):
        """Add problem list section with proper entries"""
        problems = visit.get("problem_list", [])
        if not problems:
            return

        component = SubElement(structured_body, "component")
        section = SubElement(component, "section")

        # Template ID
        template_id = SubElement(section, "templateId")
        template_id.set("root", self.PROBLEM_SECTION_TEMPLATE)

        # Code
        code = SubElement(section, "code")
        code.set("code", "11450-4")
        code.set("codeSystem", self.LOINC_SYSTEM)
        code.set("displayName", "Problem List")

        # Title
        title = SubElement(section, "title")
        title.text = "Problem List"

        # Text (narrative)
        text = SubElement(section, "text")
        list_elem = SubElement(text, "list")
        for problem in problems:
            item = SubElement(list_elem, "item")
            item.text = problem.get("problem", "")

        # Entries (structured)
        for i, problem in enumerate(problems):
            self._add_problem_entry(section, problem, i)

    def _add_problem_entry(self, section: Element, problem: Dict[str, Any], index: int):
        """Add a structured problem entry with Problem Concern Act template"""
        entry = SubElement(section, "entry")
        entry.set("typeCode", "DRIV")

        # Problem Concern Act
        act = SubElement(entry, "act")
        act.set("classCode", "ACT")
        act.set("moodCode", "EVN")

        # Template ID
        template_id = SubElement(act, "templateId")
        template_id.set("root", self.PROBLEM_CONCERN_ACT_TEMPLATE)

        # ID
        act_id = SubElement(act, "id")
        act_id.set("root", "2.16.840.1.113883.19")
        act_id.set("extension", f"problem_act_{index}")

        # Code
        code = SubElement(act, "code")
        code.set("code", "CONC")
        code.set("codeSystem", "2.16.840.1.113883.5.6")

        # Status code
        status_code = SubElement(act, "statusCode")
        status_code.set("code", "active")

        # Effective time
        effective_time = SubElement(act, "effectiveTime")
        low = SubElement(effective_time, "low")
        low.set("nullFlavor", "UNK")

        # Entry relationship - Problem Observation
        entry_relationship = SubElement(act, "entryRelationship")
        entry_relationship.set("typeCode", "SUBJ")

        observation = SubElement(entry_relationship, "observation")
        observation.set("classCode", "OBS")
        observation.set("moodCode", "EVN")

        # Template ID
        obs_template = SubElement(observation, "templateId")
        obs_template.set("root", self.PROBLEM_OBSERVATION_TEMPLATE)

        # ID
        obs_id = SubElement(observation, "id")
        obs_id.set("root", "2.16.840.1.113883.19")
        obs_id.set("extension", f"problem_obs_{index}")

        # Code
        obs_code = SubElement(observation, "code")
        obs_code.set("code", "55607006")
        obs_code.set("codeSystem", self.SNOMED_SYSTEM)
        obs_code.set("displayName", "Problem")

        # Status code
        obs_status = SubElement(observation, "statusCode")
        obs_status.set("code", "completed")

        # Effective time
        obs_time = SubElement(observation, "effectiveTime")
        obs_low = SubElement(obs_time, "low")
        obs_low.set("nullFlavor", "UNK")

        # Value (SNOMED code if available)
        value = SubElement(observation, "value")
        value.set(f"{{{self.XSI_NAMESPACE}}}type", "CD")

        # Try to find SNOMED code
        problem_text = problem.get("problem", "").lower()
        snomed_code = self._find_snomed_code(problem_text)

        if snomed_code:
            value.set("code", snomed_code[0])
            value.set("codeSystem", self.SNOMED_SYSTEM)
            value.set("displayName", snomed_code[1])
        else:
            value.set("nullFlavor", "OTH")
            value.set("displayName", problem.get("problem", ""))

    def _add_results_section(self, structured_body: Element, visit: Dict[str, Any]):
        """Add results section with organizer"""
        results = visit.get("results", [])
        if not results:
            return

        component = SubElement(structured_body, "component")
        section = SubElement(component, "section")

        # Template ID
        template_id = SubElement(section, "templateId")
        template_id.set("root", self.RESULTS_SECTION_TEMPLATE)

        # Code
        code = SubElement(section, "code")
        code.set("code", "30954-2")
        code.set("codeSystem", self.LOINC_SYSTEM)
        code.set("displayName", "Relevant diagnostic tests and/or laboratory data")

        # Title
        title = SubElement(section, "title")
        title.text = "Results"

        # Text (narrative table)
        text = SubElement(section, "text")
        table = SubElement(text, "table")
        table.set("border", "1")
        table.set("width", "100%")

        # Table header
        thead = SubElement(table, "thead")
        tr = SubElement(thead, "tr")
        for header in ["Test", "Value", "Units", "Notes"]:
            th = SubElement(tr, "th")
            th.text = header

        # Table body
        tbody = SubElement(table, "tbody")
        for result in results:
            tr = SubElement(tbody, "tr")

            td_test = SubElement(tr, "td")
            td_test.text = result.get("test_name", "")

            td_value = SubElement(tr, "td")
            td_value.text = str(result.get("value", ""))

            td_unit = SubElement(tr, "td")
            td_unit.text = result.get("unit", "")

            td_notes = SubElement(tr, "td")
            if result.get("abnormal_flag") and result["abnormal_flag"] != "normal":
                td_notes.text = f"Abnormal: {result['abnormal_flag']}"

        # Structured entry - Organizer
        entry = SubElement(section, "entry")
        entry.set("typeCode", "DRIV")

        organizer = SubElement(entry, "organizer")
        organizer.set("classCode", "CLUSTER")
        organizer.set("moodCode", "EVN")

        # Template ID
        org_template = SubElement(organizer, "templateId")
        org_template.set("root", self.RESULTS_ORGANIZER_TEMPLATE)

        # ID
        org_id = SubElement(organizer, "id")
        org_id.set("root", "2.16.840.1.113883.19")
        org_id.set("extension", f"results_org_{uuid.uuid4().hex[:8]}")

        # Code
        org_code = SubElement(organizer, "code")
        org_code.set("code", "18719-5")
        org_code.set("codeSystem", self.LOINC_SYSTEM)
        org_code.set("displayName", "Chemistry studies")

        # Status code
        org_status = SubElement(organizer, "statusCode")
        org_status.set("code", "completed")

        # Components (observations)
        for i, result in enumerate(results):
            self._add_result_observation(organizer, result, i)

    def _add_result_observation(self, organizer: Element, result: Dict[str, Any], index: int):
        """Add a result observation component"""
        component = SubElement(organizer, "component")

        observation = SubElement(component, "observation")
        observation.set("classCode", "OBS")
        observation.set("moodCode", "EVN")

        # Template ID
        template_id = SubElement(observation, "templateId")
        template_id.set("root", self.RESULT_OBSERVATION_TEMPLATE)

        # ID
        obs_id = SubElement(observation, "id")
        obs_id.set("root", "2.16.840.1.113883.19")
        obs_id.set("extension", f"result_obs_{index}")

        # Code (LOINC if available)
        code = SubElement(observation, "code")
        test_name = result.get("test_name", "").lower()
        loinc_code = self._find_loinc_code(test_name)

        if loinc_code:
            code.set("code", loinc_code[0])
            code.set("codeSystem", self.LOINC_SYSTEM)
            code.set("displayName", loinc_code[1])
        else:
            code.set("nullFlavor", "OTH")
            code.set("displayName", result.get("test_name", ""))

        # Status code
        status_code = SubElement(observation, "statusCode")
        status_code.set("code", "completed")

        # Effective time
        effective_time = SubElement(observation, "effectiveTime")
        effective_time.set("nullFlavor", "UNK")

        # Value
        value = SubElement(observation, "value")
        value.set(f"{{{self.XSI_NAMESPACE}}}type", "PQ")
        value.set("value", str(result.get("value", "")))
        value.set("unit", result.get("unit", "1"))

    def _add_assessment_section(self, structured_body: Element, visit: Dict[str, Any]):
        """Add assessment section"""
        if not visit.get("assessment"):
            return

        component = SubElement(structured_body, "component")
        section = SubElement(component, "section")

        # Code
        code = SubElement(section, "code")
        code.set("code", "51848-0")
        code.set("codeSystem", self.LOINC_SYSTEM)
        code.set("displayName", "Assessment")

        # Title
        title = SubElement(section, "title")
        title.text = "Assessment"

        # Text
        text = SubElement(section, "text")
        paragraph = SubElement(text, "paragraph")
        paragraph.text = visit["assessment"]

    def _add_plan_section(self, structured_body: Element, visit: Dict[str, Any]):
        """Add plan of care section"""
        plan = visit.get("plan", [])
        if not plan:
            return

        component = SubElement(structured_body, "component")
        section = SubElement(component, "section")

        # Code
        code = SubElement(section, "code")
        code.set("code", "18776-5")
        code.set("codeSystem", self.LOINC_SYSTEM)
        code.set("displayName", "Plan of care note")

        # Title
        title = SubElement(section, "title")
        title.text = "Plan"

        # Text
        text = SubElement(section, "text")
        list_elem = SubElement(text, "list")
        for plan_item in plan:
            item = SubElement(list_elem, "item")
            item.text = plan_item.get("action", "")

    def _parse_name(self, full_name: str) -> Dict[str, str]:
        """Parse full name into given and family names"""
        parts = full_name.strip().split()
        if len(parts) == 1:
            return {"given": "", "family": parts[0]}
        elif len(parts) >= 2:
            return {"given": " ".join(parts[:-1]), "family": parts[-1]}
        else:
            return {"given": "", "family": full_name}

    def _find_snomed_code(self, problem_text: str) -> Optional[tuple]:
        """Find SNOMED code for a problem"""
        for key, code in self.SNOMED_CODES.items():
            if key in problem_text:
                return (code, key.title())
        return None

    def _find_loinc_code(self, test_name: str) -> Optional[tuple]:
        """Find LOINC code for a lab test"""
        for key, code in self.LOINC_CODES.items():
            if key in test_name:
                return (code, key.title())
        return None

    def _prettify_xml(self, elem: Element) -> str:
        """Convert XML element to pretty-printed string"""
        rough_string = tostring(elem, encoding='utf-8')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ", encoding="UTF-8").decode('utf-8')


class RenderError(Exception):
    """Raised when rendering fails"""
    pass
