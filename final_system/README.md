# Medical PDF → CCD/CCDA Converter

Enterprise-grade medical document processing system that converts PDF medical records into standardized HL7 CCD/CCDA XML format with professional human-readable reports.

## Overview

This system automates the conversion of medical PDF documents into structured, standards-compliant formats suitable for electronic health record (EHR) integration and clinical review.

### Key Capabilities

- **Intelligent OCR**: Advanced optical character recognition optimized for medical documents including handwritten notes
- **Automated Structuring**: Extracts medications, diagnoses, lab results, vital signs, and treatment plans
- **HL7 CCD/CCDA Generation**: Creates standards-compliant XML documents following CCD R2.1 specifications
- **Professional Reports**: Generates human-readable PDF summaries in clinical consultation format
- **Multiple Output Formats**: XML (CCD/CCDA), PDF (clinical summary), DOCX (editable report), JSON (structured data)

## Quick Start

### Prerequisites

- Python 3.9 or higher
- Internet connection (for API access)
- Gemini API key ([Get one here](https://makersuite.google.com/app/apikey))

### Installation

**Linux/macOS:**
```bash
./setup.sh
```

**Windows:**
```bash
bash setup.sh
```

The setup script will automatically:
1. Check Python installation
2. Create virtual environment
3. Install all dependencies
4. Create configuration template

### Configuration

1. Edit the `.env` file:
```bash
GEMINI_API_KEY=your-api-key-here
```

2. (Optional) Customize model settings in `.env` if needed

### Running the Application

**Linux/macOS:**
```bash
./run.sh
```

**Windows:**
```bash
bash run.sh
```

The web interface will automatically open in your browser at `http://localhost:8501`

## Usage

1. **Upload PDF**: Click "Browse files" and select your medical PDF document (max 200MB)
2. **Process**: Click "Process Document" button
3. **Download**:
   - Use "Download All Files (ZIP)" for complete package
   - Or download individual files (XML, PDF, DOCX, JSON)

### Processing Time

Processing time varies by document length:
- 1-5 pages: 30-60 seconds
- 6-20 pages: 1-3 minutes
- 20+ pages: 3-5 minutes

## Output Files

For each processed document, the system generates:

| File | Format | Description |
|------|--------|-------------|
| `*_ccd.xml` | XML | HL7 CCD/CCDA R2.1 compliant XML document |
| `*_report.pdf` | PDF | Professional clinical summary report |
| `*_report.docx` | DOCX | Editable Word document |
| `*_canonical.json` | JSON | Structured data in canonical format |
| `*_ocr.txt` | TXT | Raw OCR text from all pages |

## System Requirements

### Minimum Requirements
- **OS**: Windows 10+, macOS 10.15+, or Linux (Ubuntu 20.04+)
- **RAM**: 4 GB
- **Disk Space**: 2 GB free space
- **Internet**: Stable connection required

### Recommended Requirements
- **RAM**: 8 GB or more
- **Disk Space**: 5 GB free space
- **Internet**: High-speed broadband

## Supported Document Types

- Outpatient consultation notes
- Hospital discharge summaries
- Laboratory reports
- Diagnostic test results
- Progress notes
- Treatment plans

## Data Privacy & Security

- All processing occurs through secure API connections
- No data is permanently stored on external servers
- Local output files are saved only on your machine
- Review Google's [data privacy policy](https://ai.google.dev/terms) for API usage

## Troubleshooting

### Application won't start
- Ensure Python 3.9+ is installed: `python3 --version`
- Re-run setup: `./setup.sh`
- Check `.env` file exists and contains valid API key

### Processing fails
- Verify API key is correct in `.env`
- Check PDF file is not password-protected
- Ensure PDF file size is under 200MB
- Verify internet connection

### Poor OCR accuracy
- Ensure PDF has good image quality (300 DPI recommended)
- Avoid highly compressed or low-resolution scans
- Check that text is clearly legible

## Support

For technical assistance:
1. Check the [SETUP.md](SETUP.md) guide for detailed installation steps
2. Review the [ARCHITECTURE.md](ARCHITECTURE.md) for system design details
3. Verify all system requirements are met

## License

Copyright © 2025. All rights reserved.

Proprietary software. Unauthorized copying, distribution, or modification is prohibited.
