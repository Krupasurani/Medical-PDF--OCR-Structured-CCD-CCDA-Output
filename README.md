# Medical PDF → OCR → Structured CCD/CCDA Output

Convert scanned medical PDFs into structured clinical documents with AI-powered OCR and intelligent medical data extraction.

## Overview

This system processes medical PDFs (handwritten + printed) and generates:
- **Canonical JSON** (single source of truth)
- **CCD/CCDA-style XML** (structure-compatible)
- **Human-readable documents** (PDF/DOCX)

## Key Features

- ✅ Vision-based OCR (Gemini 3 Preview)
- ✅ Zero hallucination policy
- ✅ Medical data structuring (Gemini 2.5 Flash)
- ✅ Visit/encounter chunking
- ✅ Deduplication & conflict detection
- ✅ Deterministic, repeatable results
- ✅ Local processing (privacy-first)

## Quick Start

### 1. Installation

```bash
# Clone repository
git clone <repository-url>
cd Medical-PDF--OCR-Structured-CCD-CCDA-Output

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your Gemini API key
# Get key from: https://ai.google.dev/
```

### 3. Run Processing (Milestone 1)

```bash
# Process a medical PDF
python main.py --input sample.pdf --output output/

# Output files:
# - output/canonical.json
# - output/debug/ (if DEBUG=true)
```

## Project Status

### ✅ Milestone 1: Core Pipeline (Current)
- [x] Project setup
- [ ] OCR integration (Gemini 3 Preview)
- [ ] Chunking engine
- [ ] Canonical JSON schema
- [ ] Unit tests

### 🔜 Milestone 2: Rendering & UI
- [ ] XML renderer
- [ ] Human-readable renderer
- [ ] Streamlit UI

### 🔜 Milestone 3: Production Hardening
- [ ] Error handling
- [ ] Performance optimization
- [ ] Complete documentation

## Documentation

- [LLM System Prompt](LLM_SYSTEM_PROMPT.md) - Direct LLM instructions
- [Architecture](ARCHITECTURE.md) - System design
- [Technical Spec](LLM_TECHNICAL_SPEC.md) - Comprehensive specification

## Technology Stack

- **Python:** 3.10+ (3.11 recommended)
- **OCR:** Gemini 3 Preview (vision-based)
- **Structuring:** Gemini 2.5 Flash
- **Schema:** Pydantic v2
- **Testing:** pytest

## Requirements

- Python 3.10+
- Gemini API key
- 8GB+ RAM (16GB recommended)
- 10GB+ free disk space

## License

Internal project - All rights reserved

## Contact

**Owner:** Krupali Surani
**Project:** Medical PDF Processing Pipeline
