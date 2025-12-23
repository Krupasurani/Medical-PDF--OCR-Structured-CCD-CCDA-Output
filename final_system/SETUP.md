# 🚀 Quick Setup Guide

Get started with Medical PDF → CCD/CCDA Converter in 3 easy steps!

---

## Step 1: Get Your Gemini API Key

1. **Go to Google AI Studio**: https://makersuite.google.com/app/apikey
2. **Sign in** with your Google account
3. **Click** "Create API Key"
4. **Copy** the API key (starts with `AIza...`)

💡 **Keep this key safe!** You'll need it in the next step.

---

## Step 2: Configure the System

### Option A: Automatic Setup (Recommended)

**Windows:**
```bash
# Just run this - it will create .env for you
start.bat
```

**Linux/Mac:**
```bash
# Just run this - it will create .env for you
./start.sh
```

When prompted, edit `.env` and paste your API key.

### Option B: Manual Setup

1. **Copy the template:**
   ```bash
   cp .env.example .env
   ```

2. **Edit .env** and add your API key:
   ```env
   GEMINI_API_KEY=AIzaSyD...your_actual_key_here
   ```

3. **Save** the file

---

## Step 3: Start the Application

### Windows
```bash
start.bat
```

### Linux/Mac
```bash
./start.sh
```

### Manual Start (Any Platform)
```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

---

## ✅ You're Ready!

The application will open in your browser at:
```
http://localhost:8501
```

### First Steps:
1. 📤 **Upload** a medical PDF
2. 🚀 **Click** "Process Document"
3. 📥 **Download** your CCD/CCDA XML!

---

## 🆘 Troubleshooting

### "No module named 'streamlit'"
```bash
pip install -r requirements.txt
```

### "Gemini API key not found"
- Make sure you created `.env` file
- Make sure you added `GEMINI_API_KEY=your_key` to `.env`
- No quotes needed around the key

### Port 8501 already in use
```bash
streamlit run app.py --server.port 8502
```

### PDF processing fails (Windows)
- Download Poppler: https://github.com/oschwartz10612/poppler-windows/releases
- Extract and add `bin` folder to PATH

---

## 📚 Next Steps

- Read [README.md](README.md) for full documentation
- Check the **Documentation** tab in the web UI
- See example outputs in the `outputs/` folder

---

## 🎯 What You Get

For each PDF you process:

- ✅ **CCD/CCDA XML** - Standards-compliant medical record
- ✅ **PDF Report** - Human-readable clinical summary
- ✅ **DOCX File** - Editable Microsoft Word document
- ✅ **Canonical JSON** - Structured data in JSON format
- ✅ **Raw OCR Text** - Complete text extraction

All with enterprise features:
- Honest confidence scoring
- Source text traceability
- Explainable deduplication
- LLM-based XML generation

---

**That's it! You're ready to process medical documents.** 🎉
