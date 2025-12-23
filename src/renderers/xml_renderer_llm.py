"""LLM-Based XML Renderer for CCD/CCDA R2.1 Compliant Output

Uses Gemini with a detailed prompt to generate Practice Fusion-compatible
CCD/CCDA XML from canonical JSON. This approach is more flexible than
programmatic XML generation.

CRITICAL: This is a RENDERER ONLY - generates output from canonical JSON.
NO data extraction logic allowed here.
"""

import json
from datetime import datetime
from typing import Dict, Any

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from ..models.canonical_schema import MedicalDocument
from ..utils.config import get_config
from ..utils.logger import get_logger

logger = get_logger(__name__)


# CCD/CCDA XML Generation Prompt
CCD_GENERATION_PROMPT = """# CCD/CCDA XML Generation Task

You are generating a CCD/CCDA R2.1 compliant XML document from medical data.

**INPUT**: You will receive EITHER raw OCR text from medical documents OR structured JSON data.
- If receiving OCR text: Extract relevant medical information and structure it into the XML format
- If receiving JSON: Use the structured data to populate the XML template

## CRITICAL REQUIREMENTS

1. **Generate BOTH narrative text AND structured entries** for each section
2. **Use exact template structure** provided below
3. **NO medical code guessing** - use only text descriptions when codes are unknown
4. **Preserve clinical uncertainty** - keep "??", "?", "R/O", "[UNCLEAR]" notations exactly as written
5. **Return ONLY valid XML** - no explanations, no markdown, just the XML
6. **Extract from OCR text**: When given OCR text, identify clinical sections (Reason for Visit, HPI, Problem List, Results, Assessment, Plan) and extract information accordingly

---

## OUTPUT XML STRUCTURE

### HEADER (Required)
```xml
<?xml version="1.0" encoding="UTF-8"?>
<ClinicalDocument xmlns="urn:hl7-org:v3" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <typeId root="2.16.840.1.113883.1.3" extension="POCD_HD000040"/>
  <templateId root="2.16.840.1.113883.10.20.22.1.1"/>
  <id root="2.16.840.1.113883.19" extension="doc_{{TIMESTAMP}}"/>
  <code code="34133-9" codeSystem="2.16.840.1.113883.6.1" displayName="Summarization of Episode Note"/>
  <title>Continuity of Care Document (CCD)</title>
  <effectiveTime value="{{YYYYMMDDHHMMSS}}"/>
  <confidentialityCode code="N" codeSystem="2.16.840.1.113883.5.25"/>
  <languageCode code="en-US"/>

  <recordTarget>
    <patientRole>
      <id nullFlavor="UNK"/>
      <patient>
        <name nullFlavor="UNK"/>
        <birthTime nullFlavor="UNK"/>
        <administrativeGenderCode code="U" codeSystem="2.16.840.1.113883.5.1"/>
      </patient>
    </patientRole>
  </recordTarget>

  <author>
    <time value="{{YYYYMMDDHHMMSS}}"/>
    <assignedAuthor>
      <id root="2.16.840.1.113883.19" extension="ocr_system"/>
      <assignedPerson>
        <name>OCR Processing System</name>
      </assignedPerson>
    </assignedAuthor>
  </author>

  <custodian>
    <assignedCustodian>
      <representedCustodianOrganization>
        <id root="2.16.840.1.113883.19" extension="org_001"/>
        <name>Medical Records Processing</name>
      </representedCustodianOrganization>
    </assignedCustodian>
  </custodian>
```

### STRUCTURED BODY

```xml
  <component>
    <structuredBody>
```

### REASON FOR VISIT SECTION
```xml
      <component>
        <section>
          <templateId root="2.16.840.1.113883.10.20.22.2.12"/>
          <code code="29299-5" codeSystem="2.16.840.1.113883.6.1" displayName="Reason for visit"/>
          <title>Reason for Visit</title>
          <text>
            <paragraph>{{REASON_FOR_VISIT_TEXT}}</paragraph>
          </text>
        </section>
      </component>
```

### HISTORY OF PRESENT ILLNESS SECTION
```xml
      <component>
        <section>
          <code code="10164-2" codeSystem="2.16.840.1.113883.6.1" displayName="History of Present Illness"/>
          <title>History of Present Illness</title>
          <text>
            <paragraph>{{HPI_TEXT}}</paragraph>
          </text>
        </section>
      </component>
```

### PROBLEM LIST SECTION (CRITICAL - NEEDS TEXT AND ENTRIES)
```xml
      <component>
        <section>
          <templateId root="2.16.840.1.113883.10.20.22.2.5.1"/>
          <code code="11450-4" codeSystem="2.16.840.1.113883.6.1" displayName="Problem List"/>
          <title>Problem List</title>
          <text>
            <list>
              {{FOR EACH PROBLEM}}
              <item>{{PROBLEM_TEXT}}</item>
            </list>
          </text>
          {{FOR EACH PROBLEM - GENERATE ENTRY}}
          <entry typeCode="DRIV">
            <act classCode="ACT" moodCode="EVN">
              <templateId root="2.16.840.1.113883.10.20.22.4.3"/>
              <id root="2.16.840.1.113883.19" extension="problem_{{INDEX}}"/>
              <code code="CONC" codeSystem="2.16.840.1.113883.5.6"/>
              <statusCode code="active"/>
              <entryRelationship typeCode="SUBJ">
                <observation classCode="OBS" moodCode="EVN">
                  <templateId root="2.16.840.1.113883.10.20.22.4.4"/>
                  <id root="2.16.840.1.113883.19" extension="problem_obs_{{INDEX}}"/>
                  <code code="55607006" codeSystem="2.16.840.1.113883.6.96" displayName="Problem"/>
                  <text>{{PROBLEM_TEXT}}</text>
                  <statusCode code="completed"/>
                </observation>
              </entryRelationship>
            </act>
          </entry>
        </section>
      </component>
```

### RESULTS SECTION (CRITICAL - NEEDS TEXT TABLE AND ENTRIES)
```xml
      <component>
        <section>
          <templateId root="2.16.840.1.113883.10.20.22.2.3.1"/>
          <code code="30954-2" codeSystem="2.16.840.1.113883.6.1" displayName="Relevant diagnostic tests and/or laboratory data"/>
          <title>Results</title>
          <text>
            <table>
              <thead>
                <tr>
                  <th>Test</th>
                  <th>Value</th>
                  <th>Unit</th>
                </tr>
              </thead>
              <tbody>
                {{FOR EACH RESULT}}
                <tr>
                  <td>{{TEST_NAME}}</td>
                  <td>{{VALUE}}</td>
                  <td>{{UNIT}}</td>
                </tr>
              </tbody>
            </table>
          </text>
          {{FOR EACH RESULT - GENERATE ORGANIZER ENTRY}}
          <entry typeCode="DRIV">
            <organizer classCode="BATTERY" moodCode="EVN">
              <templateId root="2.16.840.1.113883.10.20.22.4.1"/>
              <id root="2.16.840.1.113883.19" extension="result_organizer_{{INDEX}}"/>
              <code nullFlavor="UNK">
                <originalText>{{TEST_NAME}}</originalText>
              </code>
              <statusCode code="completed"/>
              <component>
                <observation classCode="OBS" moodCode="EVN">
                  <templateId root="2.16.840.1.113883.10.20.22.4.2"/>
                  <id root="2.16.840.1.113883.19" extension="result_obs_{{INDEX}}"/>
                  <code nullFlavor="UNK">
                    <originalText>{{TEST_NAME}}</originalText>
                  </code>
                  <statusCode code="completed"/>
                  <effectiveTime nullFlavor="UNK"/>
                  <value xsi:type="PQ" value="{{VALUE}}" unit="{{UNIT or '1'}}"/>
                </observation>
              </component>
            </organizer>
          </entry>
        </section>
      </component>
```

### ASSESSMENT SECTION
```xml
      <component>
        <section>
          <code code="51848-0" codeSystem="2.16.840.1.113883.6.1" displayName="Assessment"/>
          <title>Assessment</title>
          <text>
            <paragraph>{{ASSESSMENT_TEXT}}</paragraph>
          </text>
        </section>
      </component>
```

### PLAN SECTION
```xml
      <component>
        <section>
          <code code="18776-5" codeSystem="2.16.840.1.113883.6.1" displayName="Plan of Care"/>
          <title>Plan</title>
          <text>
            <list>
              {{FOR EACH PLAN ITEM}}
              <item>{{PLAN_ACTION}}</item>
            </list>
          </text>
        </section>
      </component>
```

### CLOSING TAGS
```xml
    </structuredBody>
  </component>
</ClinicalDocument>
```

---

## GENERATION RULES

### DO:
✅ Generate BOTH `<text>` (human-readable) AND `<entry>` (structured) for Problems and Results
✅ Use `nullFlavor="UNK"` when codes are unknown
✅ Use `<originalText>` tags for test names without LOINC codes
✅ Preserve all clinical uncertainty markers ("??", "R/O", "Possible")
✅ Generate unique sequential IDs (problem_001, problem_002, result_organizer_001, etc.)
✅ Use current timestamp for effectiveTime

### DON'T:
❌ DO NOT guess SNOMED, ICD-10, or LOINC codes
❌ DO NOT remove uncertainty qualifiers
❌ DO NOT create entries without corresponding text blocks
❌ DO NOT add explanations or markdown - output ONLY XML
❌ DO NOT skip the structured `<entry>` blocks for problems and results

---

## INPUT DATA

The medical data is provided below in JSON format. Generate the complete CCD/CCDA XML document following the structure above.
"""


class XMLRenderer:
    """LLM-based XML renderer for CCD/CCDA R2.1 compliant output"""

    def __init__(self):
        self.config = get_config()
        genai.configure(api_key=self.config.gemini_api_key)
        self.model = genai.GenerativeModel(self.config.structuring_model_name)
        logger.info("XML renderer initialized (LLM-based CCD/CCDA R2.1)")

    def render(self, document: MedicalDocument) -> str:
        """Render MedicalDocument to CCD/CCDA XML using LLM

        Args:
            document: Validated MedicalDocument instance

        Returns:
            XML string (CCD/CCDA R2.1 compliant)
        """
        logger.info("Rendering document to XML (LLM-based)", visits=len(document.visits))

        try:
            # Generate timestamp
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

            # Use raw OCR text if available, otherwise fall back to JSON
            if document.raw_ocr_text:
                logger.info("Using raw OCR text for XML generation (preferred - more context)")

                # Build prompt with raw OCR text
                prompt = f"""{CCD_GENERATION_PROMPT}

TIMESTAMP: {timestamp}

INPUT DATA (RAW OCR TEXT FROM MEDICAL DOCUMENT):
{document.raw_ocr_text}

Generate the complete CCD/CCDA XML document now. Output ONLY the XML, no explanations.
"""
            else:
                logger.info("Using canonical JSON for XML generation (fallback - less context)")
                llm_input = self._prepare_llm_input(document)

                # Build prompt with JSON
                prompt = f"""{CCD_GENERATION_PROMPT}

TIMESTAMP: {timestamp}

INPUT DATA (CANONICAL JSON):
```json
{json.dumps(llm_input, indent=2)}
```

Generate the complete CCD/CCDA XML document now. Output ONLY the XML, no explanations.
"""

            # Call LLM
            logger.info("Calling LLM for XML generation...")
            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.0,  # Deterministic
                    top_p=1.0,
                    top_k=1,
                    max_output_tokens=16384,
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

            # Extract XML
            xml_content = response.text.strip()

            # Remove markdown code blocks if present
            if xml_content.startswith("```xml"):
                xml_content = xml_content[6:]
            if xml_content.startswith("```"):
                xml_content = xml_content[3:]
            if xml_content.endswith("```"):
                xml_content = xml_content[:-3]

            xml_content = xml_content.strip()

            # Ensure it starts with <?xml
            if not xml_content.startswith("<?xml"):
                xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_content

            logger.info("XML generation complete (LLM-based)", size_bytes=len(xml_content))
            return xml_content

        except Exception as e:
            logger.error("LLM-based XML rendering failed", error=str(e))
            raise RenderError(f"Failed to render XML via LLM: {e}")

    def _prepare_llm_input(self, document: MedicalDocument) -> Dict[str, Any]:
        """Prepare simplified data structure for LLM

        Args:
            document: MedicalDocument instance

        Returns:
            Simplified dict for LLM consumption
        """
        # Convert document to dict and extract relevant fields
        visits_data = []

        for visit in document.visits:
            visit_dict = {
                "visit_id": visit.get("visit_id"),
                "visit_date": visit.get("visit_date"),
                "reason_for_visit": visit.get("reason_for_visit"),
                "history_of_present_illness": visit.get("history_of_present_illness"),
                "problem_list": visit.get("problem_list", []),
                "results": visit.get("results", []),
                "assessment": visit.get("assessment"),
                "plan": visit.get("plan", []),
            }
            visits_data.append(visit_dict)

        return {
            "patient_name": document.document_metadata.patient_name,
            "patient_id": document.document_metadata.patient_id,
            "dob": str(document.document_metadata.dob) if document.document_metadata.dob else None,
            "sex": document.document_metadata.sex,
            "visits": visits_data,
        }


class RenderError(Exception):
    """Raised when rendering fails"""
    pass
