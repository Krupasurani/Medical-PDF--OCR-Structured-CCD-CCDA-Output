#!/usr/bin/env python3
"""
Fixed Quick OCR Test - No Hanging
Uses fast model + proper timeout + optimizations
"""

import os
import sys
from pathlib import Path
from PIL import Image
import io
import base64
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pdf2image import convert_from_path
import time

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("Error: GEMINI_API_KEY not found in .env")
    sys.exit(1)

# Create client ONCE with long timeout
client = genai.Client(
    api_key=GEMINI_API_KEY,
    http_options=types.HttpOptions(timeout=600_000)  # 600 seconds = 10 minutes (in ms)
)

# Safety settings (keep as you had)
safety_settings = [
    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=types.HarmBlockThreshold.BLOCK_NONE),
    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
]

def image_to_base64(image: Image.Image) -> str:
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def extract_text_quick(image: Image.Image, page_num: int) -> str:
    prompt = "Extract all text from this medical document. Return all the text, and symbols exactly as written."

    # Resize to reduce processing time (Gemini handles up to ~2048px well)
    image = image.copy()
    image.thumbnail((2048, 2048), Image.Resampling.LANCZOS)

    image_b64 = image_to_base64(image)

    print(f"   Sending request to Gemini API (page {page_num})...")
    start = time.time()

    try:
        response = client.models.generate_content(
            model="gemini-3-pro-preview",  # Fast & great for OCR; change to -pro- if you need higher accuracy
            contents=[
                types.Part(text=prompt),
                types.Part(
                    inline_data=types.Blob(
                        mime_type="image/png",
                        data=image_b64
                    )
                )
            ],
            config=types.GenerateContentConfig(
                temperature=0,
                safety_settings=safety_settings
            )
        )

        elapsed = time.time() - start
        extracted_text = response.text.strip()
        print(f"   ✓ Response in {elapsed:.1f}s ({len(extracted_text)} chars)")
        return extracted_text

    except Exception as e:
        elapsed = time.time() - start
        print(f"   ❌ Error after {elapsed:.1f}s: {type(e).__name__}: {e}")
        return ""

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_ocr_quick_fixed.py <pdf_path> [page_number]")
        sys.exit(1)

    pdf_path = sys.argv[1]
    test_page = int(sys.argv[2]) if len(sys.argv) > 2 else None

    print("=" * 70)
    print("⚡ FIXED QUICK OCR TEST (No Hanging)")
    print("=" * 70)
    print(f"PDF: {pdf_path}")
    print(f"Model: gemini-1.5-flash-latest")

    # Convert PDF with reasonable DPI
    print(f"\n📄 Converting PDF to images (DPI=200)...")
    images = convert_from_path(pdf_path, dpi=200)
    print(f"✓ Converted {len(images)} pages")

    if test_page:
        pages_to_test = [(test_page, images[test_page - 1])]
        print(f"\n📖 Testing only page {test_page}")
    else:
        pages_to_test = list(enumerate(images, start=1))
        print(f"\n📖 Testing all {len(images)} pages")

    results = []
    output_dir = Path("ocr_test_quick_fixed")
    output_dir.mkdir(exist_ok=True)

    for page_num, image in pages_to_test:
        print(f"\n[{page_num}/{len(images)}] Processing Page {page_num}")

        text = extract_text_quick(image, page_num)

        if text:
            output_file = output_dir / f"page_{page_num}.txt"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(f"PAGE {page_num}\n")
                f.write("=" * 70 + "\n\n")
                f.write(text)
            print(f"   ✓ Saved: {output_file}")
            results.append({"page": page_num, "chars": len(text), "success": True})
        else:
            results.append({"page": page_num, "success": False})

    # Summary
    print("\n" + "=" * 70)
    print("📊 SUMMARY")
    print("=" * 70)
    successful = sum(1 for r in results if r.get("success"))
    print(f"Successfully processed: {successful}/{len(results)} pages")
    total_chars = sum(r.get("chars", 0) for r in results if r.get("success"))
    print(f"Total characters extracted: {total_chars}")
    print(f"\n✅ Results saved in: {output_dir}/")

if __name__ == "__main__":
    main()