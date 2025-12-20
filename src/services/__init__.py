"""Core processing services"""

from .pdf_service import PDFService
from .ocr_service import OCRService
from .chunking_service import ChunkingService
from .structuring_service import StructuringService

__all__ = [
    "PDFService",
    "OCRService",
    "ChunkingService",
    "StructuringService",
]


# """Services module"""

# from .pdf_service import PDFService
# from .ocr_service import EnhancedOCRService
# from .chunking_service import ChunkingService
# from .structuring_service import StructuringService

# # Backward compatibility alias
# OCRService = EnhancedOCRService

# __all__ = [
#     'PDFService',
#     'EnhancedOCRService',
#     'OCRService',
#     'ChunkingService',
#     'StructuringService',
# ]