"""Integration tests for full pipeline

Tests end-to-end processing from PDF → JSON → XML/PDF/DOCX
"""

import pytest
import tempfile
from pathlib import Path
import json
from xml.etree import ElementTree as ET

from src.services.pdf_service import PDFService
from src.services.ocr_service import OCRService
from src.services.chunking_service import ChunkingService
from src.services.structuring_service import StructuringService
from src.services.deduplication_service import DeduplicationService
from src.renderers.xml_renderer import XMLRenderer
from src.renderers.pdf_renderer import PDFRenderer
from src.renderers.docx_renderer import DOCXRenderer
from src.models.canonical_schema import MedicalDocument


class TestFullPipeline:
    """Test complete pipeline integration"""

    @pytest.fixture(scope="class")
    def services(self):
        """Initialize all services"""
        return {
            "pdf": PDFService(),
            "ocr": OCRService(),
            "chunking": ChunkingService(),
            "structuring": StructuringService(),
            "deduplication": DeduplicationService(),
            "xml_renderer": XMLRenderer(),
            "pdf_renderer": PDFRenderer(),
            "docx_renderer": DOCXRenderer(),
        }

    @pytest.fixture(scope="class")
    def sample_pdf(self):
        """Path to sample PDF for testing"""
        # Note: This should point to a real test PDF
        pdf_path = Path("sample_inputs/Sample Medical Records (1).pdf")
        if not pdf_path.exists():
            pytest.skip(f"Sample PDF not found: {pdf_path}")
        return pdf_path

    def test_pdf_to_json_pipeline(self, services, sample_pdf):
        """Test PDF → OCR → Chunking → Structuring → JSON"""
        # OCR
        ocr_results = []
        page_count = services["pdf"].get_page_count(str(sample_pdf))

        for page_num in range(1, min(page_count + 1, 3)):  # Test first 2 pages
            result = services["ocr"].process_page(str(sample_pdf), page_num)
            ocr_results.append(result)

        assert len(ocr_results) > 0, "No OCR results"
        assert all(r["raw_text"] for r in ocr_results), "Some pages have no text"

        # Chunking
        chunks = services["chunking"].chunk_by_visit(ocr_results)
        assert len(chunks) > 0, "No chunks created"

        # Structuring
        document = services["structuring"].structure_document(chunks, ocr_results)
        assert isinstance(document, MedicalDocument), "Invalid document type"
        assert len(document.visits) > 0, "No visits in document"

        # Validate JSON structure
        json_data = json.loads(document.model_dump_json())
        assert "visits" in json_data, "Missing visits in JSON"
        assert "document_metadata" in json_data, "Missing metadata in JSON"

    def test_deduplication_integration(self, services):
        """Test deduplication service integration"""
        # Create sample visits with duplicates
        visits = [
            {
                "visit_id": "visit_001",
                "medications": [
                    {"name": "Aspirin", "dose": "81mg", "source_page": 1},
                    {"name": "aspirin", "dose": "81mg", "source_page": 2},  # Duplicate
                ],
                "problem_list": [
                    {"problem": "Hypertension", "source_page": 1},
                    {"problem": "HTN", "source_page": 2},  # Fuzzy match
                ],
            }
        ]

        deduplicated = services["deduplication"].deduplicate_document(visits)

        assert len(deduplicated) == 1, "Should have 1 visit"
        assert len(deduplicated[0]["medications"]) == 1, "Should have 1 deduplicated medication"
        assert len(deduplicated[0]["problem_list"]) == 1, "Should have 1 deduplicated problem"

    def test_xml_rendering(self, services, sample_pdf):
        """Test JSON → XML rendering"""
        # Create minimal document
        document = MedicalDocument(visits=[{
            "visit_id": "test_001",
            "visit_date": "2025-01-01",
            "medications": [{"name": "Test Med", "source_page": 1}],
        }])

        # Render XML
        xml_string = services["xml_renderer"].render(document)

        assert xml_string, "XML output is empty"
        assert "ClinicalDocument" in xml_string, "Missing ClinicalDocument root"

        # Parse XML to validate structure
        root = ET.fromstring(xml_string)
        assert root.tag.endswith("ClinicalDocument"), "Invalid root tag"

    def test_pdf_rendering(self, services):
        """Test JSON → PDF rendering"""
        # Create minimal document
        document = MedicalDocument(visits=[{
            "visit_id": "test_001",
            "visit_date": "2025-01-01",
            "reason_for_visit": "Annual checkup",
        }])

        # Render PDF
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            output_path = tmp.name

        services["pdf_renderer"].render(document, output_path)

        assert Path(output_path).exists(), "PDF file not created"
        assert Path(output_path).stat().st_size > 0, "PDF file is empty"

        # Cleanup
        Path(output_path).unlink()

    def test_docx_rendering(self, services):
        """Test JSON → DOCX rendering"""
        # Create minimal document
        document = MedicalDocument(visits=[{
            "visit_id": "test_001",
            "visit_date": "2025-01-01",
            "assessment": "Patient is healthy",
        }])

        # Render DOCX
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
            output_path = tmp.name

        services["docx_renderer"].render(document, output_path)

        assert Path(output_path).exists(), "DOCX file not created"
        assert Path(output_path).stat().st_size > 0, "DOCX file is empty"

        # Cleanup
        Path(output_path).unlink()

    def test_complete_pipeline_with_all_outputs(self, services, sample_pdf):
        """Test complete pipeline: PDF → JSON → XML/PDF/DOCX"""
        # OCR (first page only for speed)
        ocr_results = [services["ocr"].process_page(str(sample_pdf), 1)]

        # Chunking
        chunks = services["chunking"].chunk_by_visit(ocr_results)

        # Structuring
        document = services["structuring"].structure_document(chunks, ocr_results)

        # Deduplication
        deduplicated_visits = services["deduplication"].deduplicate_document(
            [v.model_dump() if hasattr(v, 'model_dump') else v for v in document.visits]
        )
        document.visits = deduplicated_visits

        # Create temp directory for outputs
        output_dir = Path(tempfile.mkdtemp())

        # Render all formats
        json_path = output_dir / "test_canonical.json"
        xml_path = output_dir / "test_ccd.xml"
        pdf_path = output_dir / "test_report.pdf"
        docx_path = output_dir / "test_report.docx"

        # Save JSON
        with open(json_path, "w") as f:
            f.write(document.model_dump_json())

        # Render outputs
        xml_content = services["xml_renderer"].render(document)
        with open(xml_path, "w") as f:
            f.write(xml_content)

        services["pdf_renderer"].render(document, str(pdf_path))
        services["docx_renderer"].render(document, str(docx_path))

        # Verify all files exist
        assert json_path.exists() and json_path.stat().st_size > 0, "JSON file missing or empty"
        assert xml_path.exists() and xml_path.stat().st_size > 0, "XML file missing or empty"
        assert pdf_path.exists() and pdf_path.stat().st_size > 0, "PDF file missing or empty"
        assert docx_path.exists() and docx_path.stat().st_size > 0, "DOCX file missing or empty"

        # Cleanup
        for file in [json_path, xml_path, pdf_path, docx_path]:
            file.unlink()
        output_dir.rmdir()


class TestDeduplicationService:
    """Test deduplication service in detail"""

    @pytest.fixture
    def dedup_service(self):
        return DeduplicationService(fuzzy_threshold=0.85)

    def test_exact_match_normalization(self, dedup_service):
        """Test exact matching with whitespace normalization"""
        assert dedup_service.is_exact_match("Hypertension", "hypertension")
        assert dedup_service.is_exact_match("  HTN  ", "htn")
        assert not dedup_service.is_exact_match("Hypertension", "Diabetes")

    def test_fuzzy_match_threshold(self, dedup_service):
        """Test fuzzy matching with threshold"""
        is_match, similarity = dedup_service.is_fuzzy_match("Hypertension", "HTN")
        # HTN is too short to be fuzzy match with Hypertension
        assert similarity < 0.85

        is_match, similarity = dedup_service.is_fuzzy_match(
            "Type 2 Diabetes Mellitus",
            "Type 2 Diabetes"
        )
        assert is_match and similarity >= 0.85

    def test_medication_merge_with_conflicts(self, dedup_service):
        """Test medication merging handles conflicts"""
        meds = [
            {"name": "Metformin", "dose": "500mg", "frequency": "BID", "source_page": 1},
            {"name": "Metformin", "dose": "1000mg", "frequency": "BID", "source_page": 2},
        ]

        merged = dedup_service.merge_medications(meds)

        assert len(merged) == 1, "Should merge to single medication"
        assert "value_conflicts" in merged[0], "Should flag dose conflict"

    def test_lab_results_different_values(self, dedup_service):
        """Test lab results with different values are flagged"""
        results = [
            {"test_name": "Glucose", "value": "110", "unit": "mg/dL", "source_page": 1},
            {"test_name": "Glucose", "value": "120", "unit": "mg/dL", "source_page": 2},
        ]

        merged = dedup_service.merge_lab_results(results)

        assert len(merged) == 1, "Should merge same test"
        assert "value_conflicts" in merged[0], "Should flag value conflict"


class TestRenderers:
    """Test renderer edge cases"""

    def test_xml_renderer_empty_sections(self):
        """Test XML renderer handles empty sections"""
        renderer = XMLRenderer()
        document = MedicalDocument(visits=[{
            "visit_id": "test_001",
            "visit_date": "2025-01-01",
            # Most fields empty
        }])

        xml_string = renderer.render(document)
        assert xml_string, "Should generate XML even with empty sections"
        assert "ClinicalDocument" in xml_string

    def test_pdf_renderer_special_characters(self):
        """Test PDF renderer handles special characters"""
        renderer = PDFRenderer()
        document = MedicalDocument(visits=[{
            "visit_id": "test_001",
            "medications": [{"name": "Medication with special chars: ↑ ± ≥", "source_page": 1}],
        }])

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            output_path = tmp.name

        renderer.render(document, output_path)
        assert Path(output_path).exists()

        Path(output_path).unlink()

    def test_docx_renderer_long_text(self):
        """Test DOCX renderer handles long text"""
        renderer = DOCXRenderer()
        long_text = "This is a very long text. " * 100

        document = MedicalDocument(visits=[{
            "visit_id": "test_001",
            "history_of_present_illness": long_text,
        }])

        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
            output_path = tmp.name

        renderer.render(document, output_path)
        assert Path(output_path).exists()

        Path(output_path).unlink()
