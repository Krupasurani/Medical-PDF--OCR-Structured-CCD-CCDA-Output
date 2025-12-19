"""Unit tests for Pydantic models"""

import pytest
from datetime import date

from src.models.canonical_schema import (
    MedicalDocument,
    Visit,
    Medication,
    Problem,
    Result,
    DocumentMetadata,
)
from src.models.enums import EncounterType, ProblemStatus, AbnormalFlag


class TestDocumentMetadata:
    """Test DocumentMetadata model"""

    def test_minimal_metadata(self):
        """Test creating minimal metadata"""
        metadata = DocumentMetadata()
        assert metadata.patient_name is None
        assert metadata.dob is None

    def test_full_metadata(self):
        """Test creating full metadata"""
        metadata = DocumentMetadata(
            patient_name="John Doe",
            patient_id="MRN123456",
            dob=date(1980, 1, 1),
            sex="M",
        )
        assert metadata.patient_name == "John Doe"
        assert metadata.patient_id == "MRN123456"
        assert metadata.dob == date(1980, 1, 1)


class TestVisit:
    """Test Visit model"""

    def test_minimal_visit(self):
        """Test creating minimal visit"""
        visit = Visit(
            visit_id="visit_001",
            raw_source_pages=[1],
        )
        assert visit.visit_id == "visit_001"
        assert visit.raw_source_pages == [1]
        assert visit.medications == []

    def test_visit_id_validation(self):
        """Test visit_id must start with 'visit_'"""
        with pytest.raises(ValueError, match="visit_id must start with 'visit_'"):
            Visit(
                visit_id="invalid_001",
                raw_source_pages=[1],
            )

    def test_visit_with_medications(self):
        """Test visit with medications"""
        visit = Visit(
            visit_id="visit_001",
            raw_source_pages=[1, 2],
            medications=[
                Medication(name="Aspirin 81mg", dose="81mg", frequency="daily", source_page=1)
            ],
        )
        assert len(visit.medications) == 1
        assert visit.medications[0].name == "Aspirin 81mg"


class TestMedication:
    """Test Medication model"""

    def test_medication_required_fields(self):
        """Test medication with required fields only"""
        med = Medication(name="Metformin", source_page=1)
        assert med.name == "Metformin"
        assert med.source_page == 1
        assert med.dose is None

    def test_medication_full(self):
        """Test medication with all fields"""
        med = Medication(
            name="Lisinopril",
            dose="10mg",
            frequency="daily",
            route="PO",
            source_page=2,
        )
        assert med.name == "Lisinopril"
        assert med.dose == "10mg"
        assert med.frequency == "daily"
        assert med.route == "PO"


class TestProblem:
    """Test Problem model"""

    def test_problem_minimal(self):
        """Test problem with minimal fields"""
        problem = Problem(problem="Hypertension", source_page=1)
        assert problem.problem == "Hypertension"
        assert problem.icd10_code is None

    def test_problem_with_icd10(self):
        """Test problem with ICD-10 code"""
        problem = Problem(
            problem="Type 2 Diabetes Mellitus",
            icd10_code="E11.9",
            status=ProblemStatus.ACTIVE,
            source_page=1,
        )
        assert problem.problem == "Type 2 Diabetes Mellitus"
        assert problem.icd10_code == "E11.9"
        assert problem.status == ProblemStatus.ACTIVE


class TestResult:
    """Test Result model"""

    def test_result_minimal(self):
        """Test result with minimal fields"""
        result = Result(
            test_name="Glucose",
            value="110",
            source_page=1,
        )
        assert result.test_name == "Glucose"
        assert result.value == "110"

    def test_result_with_abnormal_flag(self):
        """Test result with abnormal flag"""
        result = Result(
            test_name="Glucose",
            value="250",
            unit="mg/dL",
            reference_range="70-100",
            abnormal_flag=AbnormalFlag.HIGH,
            source_page=3,
        )
        assert result.abnormal_flag == AbnormalFlag.HIGH
        assert result.unit == "mg/dL"


class TestMedicalDocument:
    """Test MedicalDocument model"""

    def test_empty_document(self):
        """Test creating empty document"""
        doc = MedicalDocument()
        assert doc.schema_version == "2.0"
        assert doc.visits == []
        assert doc.page_count == 0

    def test_document_with_visits(self):
        """Test document with visits"""
        doc = MedicalDocument(
            visits=[
                Visit(visit_id="visit_001", raw_source_pages=[1]),
                Visit(visit_id="visit_002", raw_source_pages=[2, 3]),
            ],
            page_count=3,
        )
        assert len(doc.visits) == 2
        assert doc.page_count == 3

    def test_document_json_export(self):
        """Test exporting document to JSON"""
        doc = MedicalDocument(
            visits=[
                Visit(
                    visit_id="visit_001",
                    raw_source_pages=[1],
                    medications=[
                        Medication(name="Aspirin", source_page=1)
                    ],
                )
            ],
            page_count=1,
        )
        json_str = doc.model_dump_json()
        assert "visit_001" in json_str
        assert "Aspirin" in json_str
        assert '"schema_version": "2.0"' in json_str

    def test_schema_version_validation(self):
        """Test schema version must be supported"""
        with pytest.raises(ValueError, match="Unsupported schema version"):
            MedicalDocument(schema_version="99.9")
