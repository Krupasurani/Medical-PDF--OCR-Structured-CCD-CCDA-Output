"""Canonical JSON Schema - Single Source of Truth

This module defines the Pydantic models for the canonical medical document format.
All outputs (XML, PDF, DOCX) MUST be rendered from these models only.

Schema Version: 2.0
"""

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from .enums import (
    AbnormalFlag,
    DocumentType,
    EncounterType,
    PlanCategory,
    ProblemStatus,
    Sex,
    TemperatureUnit,
)


class DocumentMetadata(BaseModel):
    """Patient demographics and document metadata"""

    patient_name: Optional[str] = Field(
        None,
        description="Patient full name",
        min_length=2,
        max_length=100
    )
    patient_id: Optional[str] = Field(
        None,
        description="Patient identifier (MRN, etc.)"
    )
    dob: Optional[date] = Field(
        None,
        description="Date of birth (ISO 8601)"
    )
    sex: Optional[Sex] = Field(
        None,
        description="Biological sex"
    )
    document_date: Optional[date] = Field(
        None,
        description="Document creation/service date"
    )
    document_type: Optional[DocumentType] = Field(
        None,
        description="Type of medical document"
    )
    author: Optional[str] = Field(
        None,
        description="Document author/provider name"
    )
    organization: Optional[str] = Field(
        None,
        description="Healthcare organization name"
    )


class VitalSignValue(BaseModel):
    """Single vital sign measurement"""

    value: Optional[float] = None
    unit: Optional[str] = None
    source_page: Optional[int] = Field(None, ge=1)


class BloodPressure(BaseModel):
    """Blood pressure measurement"""

    systolic: Optional[float] = Field(None, ge=40, le=300)
    diastolic: Optional[float] = Field(None, ge=20, le=200)
    unit: str = "mmHg"
    source_page: Optional[int] = Field(None, ge=1)


class VitalSigns(BaseModel):
    """Collection of vital signs"""

    temperature: Optional[VitalSignValue] = None
    blood_pressure: Optional[BloodPressure] = None
    heart_rate: Optional[VitalSignValue] = None
    respiratory_rate: Optional[VitalSignValue] = None
    oxygen_saturation: Optional[VitalSignValue] = None
    weight: Optional[VitalSignValue] = None
    height: Optional[VitalSignValue] = None
    bmi: Optional[VitalSignValue] = Field(
        None,
        description="Body Mass Index (may be calculated)"
    )


class Medication(BaseModel):
    """Medication entry"""

    name: str = Field(..., min_length=1, description="Medication name (as written)")
    dose: Optional[str] = Field(None, description="Dose amount and unit")
    frequency: Optional[str] = Field(None, description="Dosing frequency")
    route: Optional[str] = Field(None, description="Route of administration")
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    source_page: int = Field(..., ge=1, description="Source page number")


class Problem(BaseModel):
    """Medical problem/diagnosis"""

    problem: str = Field(..., min_length=1, description="Problem description (as written)")
    icd10_code: Optional[str] = Field(
        None,
        description="ICD-10 code if explicitly stated"
    )
    status: Optional[ProblemStatus] = Field(
        None,
        description="Problem status"
    )
    onset_date: Optional[date] = None
    source_page: int = Field(..., ge=1)


class Result(BaseModel):
    """Lab result or diagnostic finding"""

    test_name: str = Field(..., min_length=1)
    value: str = Field(..., description="Test value (as written)")
    unit: Optional[str] = None
    reference_range: Optional[str] = Field(
        None,
        description="Normal reference range"
    )
    abnormal_flag: Optional[AbnormalFlag] = None
    test_date: Optional[date] = None
    source_page: int = Field(..., ge=1)


class PlanItem(BaseModel):
    """Treatment plan action"""

    action: str = Field(..., min_length=1, description="Plan action (as written)")
    category: Optional[PlanCategory] = None
    source_page: int = Field(..., ge=1)


class UnclearSection(BaseModel):
    """Marker for unclear/low-confidence section"""

    section: str = Field(..., description="Section name")
    page: int = Field(..., ge=1)
    reason: str = Field(..., description="Why unclear")
    original_text: str = Field(..., description="[UNCLEAR] marker or partial text")


class Visit(BaseModel):
    """Single clinical visit/encounter"""

    visit_id: str = Field(..., description="Unique visit identifier")
    visit_date: Optional[date] = None
    encounter_type: Optional[EncounterType] = Field(
        EncounterType.UNKNOWN,
        description="Type of encounter"
    )

    # Clinical sections
    reason_for_visit: str = Field(default="", description="Chief complaint")
    history_of_present_illness: str = Field(default="", description="HPI")
    past_medical_history: List[str] = Field(default_factory=list)

    medications: List[Medication] = Field(default_factory=list)
    allergies: List[str] = Field(default_factory=list)
    vital_signs: Optional[VitalSigns] = None
    problem_list: List[Problem] = Field(default_factory=list)
    results: List[Result] = Field(default_factory=list)

    assessment: str = Field(default="", description="Clinical assessment")
    plan: List[PlanItem] = Field(default_factory=list)

    # Metadata
    raw_source_pages: List[int] = Field(
        ...,
        min_length=1,
        description="Source pages for this visit"
    )
    extraction_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Overall extraction confidence"
    )
    manual_review_required: bool = Field(
        default=False,
        description="Flag if human review needed"
    )
    review_reasons: List[str] = Field(
        default_factory=list,
        description="Why manual review needed"
    )

    @field_validator('visit_id')
    @classmethod
    def validate_visit_id(cls, v: str) -> str:
        """Ensure visit_id follows pattern"""
        if not v.startswith('visit_'):
            raise ValueError("visit_id must start with 'visit_'")
        return v


class DataQuality(BaseModel):
    """Data quality metrics and warnings"""

    completeness_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Percentage of expected fields populated"
    )
    confidence_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Overall OCR/extraction confidence"
    )
    unclear_sections: List[UnclearSection] = Field(
        default_factory=list,
        description="Sections marked as [UNCLEAR]"
    )
    missing_critical_fields: List[str] = Field(
        default_factory=list,
        description="Expected but missing fields"
    )


class MedicalDocument(BaseModel):
    """Top-level canonical medical document

    This is the single source of truth. All outputs (XML, PDF, DOCX)
    MUST be rendered from this model only.
    """

    schema_version: str = Field(
        default="2.0",
        description="Schema version"
    )
    document_metadata: DocumentMetadata = Field(
        default_factory=DocumentMetadata,
        description="Patient and document info"
    )
    visits: List[Visit] = Field(
        default_factory=list,
        description="Clinical visits/encounters"
    )
    data_quality: DataQuality = Field(
        default_factory=DataQuality,
        description="Quality metrics"
    )

    # Processing metadata
    processed_at: datetime = Field(
        default_factory=datetime.now,
        description="Processing timestamp"
    )
    processing_duration_ms: Optional[int] = Field(
        None,
        ge=0,
        description="Total processing time"
    )
    ocr_confidence_avg: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Average OCR confidence across pages"
    )
    page_count: int = Field(default=0, ge=0)
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)

    # Raw OCR text for LLM-based rendering
    raw_ocr_text: Optional[str] = Field(
        None,
        description="Complete raw OCR text from all pages (for LLM-based rendering)"
    )

    @field_validator('schema_version')
    @classmethod
    def validate_schema_version(cls, v: str) -> str:
        """Ensure schema version is supported"""
        if v not in ["2.0"]:
            raise ValueError(f"Unsupported schema version: {v}")
        return v

    def model_dump_json(self, **kwargs) -> str:
        """Export to JSON with ISO date formatting"""
        return super().model_dump_json(
            exclude_none=False,
            indent=2,
            **kwargs
        )




# """Canonical JSON Schema - Single Source of Truth

# This module defines the Pydantic models for the canonical medical document format.
# All outputs (XML, PDF, DOCX) MUST be rendered from these models only.

# Schema Version: 2.0
# """

# from datetime import date, datetime
# from typing import List, Optional
# from typing import List, Dict, Optional, Any  # ← Add 'Any' if missing
# from pydantic import BaseModel, Field, field_validator
# from typing import List, Dict, Optional
# from pydantic import BaseModel, Field
# from .enums import (
#     AbnormalFlag,
#     DocumentType,
#     EncounterType,
#     PlanCategory,
#     ProblemStatus,
#     Sex,
#     TemperatureUnit,
# )


# class DocumentMetadata(BaseModel):
#     """Patient demographics and document metadata"""

#     patient_name: Optional[str] = Field(
#         None,
#         description="Patient full name",
#         min_length=2,
#         max_length=100
#     )
#     patient_id: Optional[str] = Field(
#         None,
#         description="Patient identifier (MRN, etc.)"
#     )
#     dob: Optional[date] = Field(
#         None,
#         description="Date of birth (ISO 8601)"
#     )
#     sex: Optional[Sex] = Field(
#         None,
#         description="Biological sex"
#     )
#     document_date: Optional[date] = Field(
#         None,
#         description="Document creation/service date"
#     )
#     document_type: Optional[DocumentType] = Field(
#         None,
#         description="Type of medical document"
#     )
#     author: Optional[str] = Field(
#         None,
#         description="Document author/provider name"
#     )
#     organization: Optional[str] = Field(
#         None,
#         description="Healthcare organization name"
#     )


# class VitalSignValue(BaseModel):
#     """Single vital sign measurement"""

#     value: Optional[float] = None
#     unit: Optional[str] = None
#     source_page: Optional[int] = Field(None, ge=1)


# class BloodPressure(BaseModel):
#     """Blood pressure measurement"""

#     systolic: Optional[float] = Field(None, ge=40, le=300)
#     diastolic: Optional[float] = Field(None, ge=20, le=200)
#     unit: str = "mmHg"
#     source_page: Optional[int] = Field(None, ge=1)


# class VitalSigns(BaseModel):
#     """Collection of vital signs"""

#     temperature: Optional[VitalSignValue] = None
#     blood_pressure: Optional[BloodPressure] = None
#     heart_rate: Optional[VitalSignValue] = None
#     respiratory_rate: Optional[VitalSignValue] = None
#     oxygen_saturation: Optional[VitalSignValue] = None
#     weight: Optional[VitalSignValue] = None
#     height: Optional[VitalSignValue] = None
#     bmi: Optional[VitalSignValue] = Field(
#         None,
#         description="Body Mass Index (may be calculated)"
#     )


# class Medication(BaseModel):
#     """Medication entry"""

#     name: str = Field(..., min_length=1, description="Medication name (as written)")
#     dose: Optional[str] = Field(None, description="Dose amount and unit")
#     frequency: Optional[str] = Field(None, description="Dosing frequency")
#     route: Optional[str] = Field(None, description="Route of administration")
#     start_date: Optional[date] = None
#     end_date: Optional[date] = None
#     source_page: int = Field(..., ge=1, description="Source page number")


# class Problem(BaseModel):
#     """Medical problem/diagnosis"""

#     problem: str = Field(..., min_length=1, description="Problem description (as written)")
#     icd10_code: Optional[str] = Field(
#         None,
#         description="ICD-10 code if explicitly stated"
#     )
#     status: Optional[ProblemStatus] = Field(
#         None,
#         description="Problem status"
#     )
#     onset_date: Optional[date] = None
#     source_page: int = Field(..., ge=1)


# class Result(BaseModel):
#     """Lab result or diagnostic finding"""

#     test_name: str = Field(..., min_length=1)
#     value: str = Field(..., description="Test value (as written)")
#     unit: Optional[str] = None
#     reference_range: Optional[str] = Field(
#         None,
#         description="Normal reference range"
#     )
#     abnormal_flag: Optional[AbnormalFlag] = None
#     test_date: Optional[date] = None
#     source_page: int = Field(..., ge=1)


# class PlanItem(BaseModel):
#     """Treatment plan action"""

#     action: str = Field(..., min_length=1, description="Plan action (as written)")
#     category: Optional[PlanCategory] = None
#     source_page: int = Field(..., ge=1)


# class UnclearSection(BaseModel):
#     """Marker for unclear/low-confidence section"""

#     section: str = Field(..., description="Section name")
#     page: int = Field(..., ge=1)
#     reason: str = Field(..., description="Why unclear")
#     original_text: str = Field(..., description="[UNCLEAR] marker or partial text")


# class Visit(BaseModel):
#     """Single clinical visit/encounter"""

#     visit_id: str = Field(..., description="Unique visit identifier")
#     visit_date: Optional[date] = None
#     encounter_type: Optional[EncounterType] = Field(
#         EncounterType.UNKNOWN,
#         description="Type of encounter"
#     )

#     # Clinical sections
#     reason_for_visit: str = Field(default="", description="Chief complaint")
#     history_of_present_illness: str = Field(default="", description="HPI")
#     past_medical_history: List[str] = Field(default_factory=list)

#     medications: List[Medication] = Field(default_factory=list)
#     allergies: List[str] = Field(default_factory=list)
#     vital_signs: Optional[VitalSigns] = None
#     problem_list: List[Problem] = Field(default_factory=list)
#     results: List[Result] = Field(default_factory=list)

#     assessment: str = Field(default="", description="Clinical assessment")
#     plan: List[PlanItem] = Field(default_factory=list)

#     # Metadata
#     raw_source_pages: List[int] = Field(
#         ...,
#         min_length=1,
#         description="Source pages for this visit"
#     )
#     extraction_confidence: float = Field(
#         default=0.0,
#         ge=0.0,
#         le=1.0,
#         description="Overall extraction confidence"
#     )
#     manual_review_required: bool = Field(
#         default=False,
#         description="Flag if human review needed"
#     )
#     review_reasons: List[str] = Field(
#         default_factory=list,
#         description="Why manual review needed"
#     )

#     @field_validator('visit_id')
#     @classmethod
#     def validate_visit_id(cls, v: str) -> str:
#         """Ensure visit_id follows pattern"""
#         if not v.startswith('visit_'):
#             raise ValueError("visit_id must start with 'visit_'")
#         return v


# class DataQuality(BaseModel):
#     """Data quality metrics and warnings"""

#     completeness_score: float = Field(
#         default=0.0,
#         ge=0.0,
#         le=1.0,
#         description="Percentage of expected fields populated"
#     )
#     confidence_score: float = Field(
#         default=0.0,
#         ge=0.0,
#         le=1.0,
#         description="Overall OCR/extraction confidence"
#     )
#     unclear_sections: List[UnclearSection] = Field(
#         default_factory=list,
#         description="Sections marked as [UNCLEAR]"
#     )
#     missing_critical_fields: List[str] = Field(
#         default_factory=list,
#         description="Expected but missing fields"
#     )

# class TextBlock(BaseModel):
#     """Represents a text block with location and confidence"""
#     text: str
#     confidence: float
#     block_type: str = Field(..., description="'printed', 'handwritten', or 'mixed'")
#     section: Optional[str] = None
#     needs_reprocessing: bool = False
#     alternatives: List[str] = Field(default_factory=list)


# class PageConfidenceMap(BaseModel):
#     """Per-page confidence breakdown"""
#     overall: float
#     blocks: List[Dict[str, Any]] = Field(default_factory=list)  # ← Changed 'any' to 'Any'


# class TextVariant(BaseModel):
#     """Variant preservation for medical terms"""
#     raw_text: str
#     alternatives: List[str] = Field(default_factory=list)
#     confidence: float
#     decision: str  # 'raw_preserved', 'marked_unclear', 'multiple_variants'

# class MedicalDocument(BaseModel):
#     schema_version: str = "2.0"
#     document_metadata: DocumentMetadata
#     visits: List[Visit]
#     data_quality: DataQuality
#     processed_at: datetime
#     processing_duration_ms: int
#     ocr_confidence_avg: float
#     page_count: int
#     warnings: List[str]
#     errors: List[str]
    
#     # NEW FIELDS - Add these:
#     confidence_map: Dict[str, PageConfidenceMap] = Field(default_factory=dict)
#     manual_review_required: bool = False
#     review_reasons: List[str] = Field(default_factory=list)

#     @field_validator('schema_version')
#     @classmethod
#     def validate_schema_version(cls, v: str) -> str:
#         """Ensure schema version is supported"""
#         if v not in ["2.0"]:
#             raise ValueError(f"Unsupported schema version: {v}")
#         return v

#     def model_dump_json(self, **kwargs) -> str:
#         """Export to JSON with ISO date formatting"""
#         return super().model_dump_json(
#             exclude_none=False,
#             indent=2,
#             **kwargs
#         )
