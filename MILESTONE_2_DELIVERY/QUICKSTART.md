# ⚡ Quick Start Guide (3 Steps)

Get up and running in **3 minutes**.

---

## Step 1: Install Python & Dependencies (1 minute)

### All Platforms
```bash
# Check Python version (need 3.10+)
python --version

# If needed, download from: https://python.org
```

### Install packages
```bash
cd MILESTONE_1_DELIVERY
pip install -r requirements.txt
```

**Windows users**: If errors occur, try:
```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

---

## Step 2: Setup API Key (1 minute)

```bash
# Copy example config
cp .env.example .env

# Edit .env file and add your Gemini API key
# GEMINI_API_KEY=your_actual_key_here
```

**Get API Key**: https://aistudio.google.com/app/apikey (free tier available)

---

## Step 3: Run (1 minute)

```bash
python main.py --input your_medical.pdf --output results/
```

**Example:**
```bash
# Windows
python main.py --input "C:\Users\John\Documents\medical_record.pdf" --output results/

# Mac/Linux
python main.py --input ~/Downloads/medical_record.pdf --output results/
```

---

## ✅ Check Results

```bash
ls results/

# You should see:
# - your_pdf_name_ocr.txt         (raw OCR text)
# - your_pdf_name_canonical.json  (structured data)
```

---

## 🎯 What You Get

### OCR Text File
- Complete text extraction from all pages
- Page separators for easy navigation
- Symbols preserved (✓, →, ±, etc.)

### Canonical JSON
- Structured medical data
- Visit dates, medications, problems, labs
- Source page tracking for every field
- CCD/CCDA compatible format

---

## 🔧 Common Issues

### "No module named 'google.genai'"
```bash
pip install google-genai
```

### "PDF is password-protected"
Remove password first using PDF tools

### "Command not found: python"
Try `python3` instead of `python`

### "Permission denied"
```bash
chmod +x main.py  # Mac/Linux
```

---

## 📖 Need More Help?

- **Full Documentation**: See README.md
- **Architecture**: See ARCHITECTURE.md
- **Troubleshooting**: See README.md → Troubleshooting section

---

## 🚀 Advanced Usage

### Debug Mode (saves intermediate outputs)
```bash
python main.py --input medical.pdf --output results/ --debug
```

### Batch Processing
```bash
for file in *.pdf; do
    python main.py --input "$file" --output results/
done
```

---

**That's it! You're ready to process medical PDFs.**

For questions, check README.md or contact your technical support team.
