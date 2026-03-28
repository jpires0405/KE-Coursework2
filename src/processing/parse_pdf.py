"""
Extract text from TfL Annual Report PDF for LLM-based knowledge extraction.
Uses pdfplumber to extract text page by page.
"""

import os
import pdfplumber

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
PDF_PATH = os.path.join(BASE_DIR, "data/raw/tfl_annual_report_2024_25.pdf")
OUTPUT_DIR = os.path.join(BASE_DIR, "data/processed")


def extract_text(pdf_path=PDF_PATH):
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text and text.strip():
                pages.append({
                    "page_number": i + 1,
                    "text": text.strip()
                })
    return pages


def extract_full_text(pdf_path=PDF_PATH):
    pages = extract_text(pdf_path)
    return "\n\n".join(p["text"] for p in pages)


def save_extracted_text(pdf_path=PDF_PATH):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    pages = extract_text(pdf_path)
    output_path = os.path.join(OUTPUT_DIR, "tfl_report_text.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        for page in pages:
            f.write(f"--- Page {page['page_number']} ---\n")
            f.write(page["text"])
            f.write("\n\n")
    print(f"Extracted {len(pages)} pages to {output_path}")
    return output_path


if __name__ == "__main__":
    if not os.path.exists(PDF_PATH):
        print(f"PDF not found at {PDF_PATH}")
        print("Run 'python src/ingestion/download_tfl_report.py' first.")
    else:
        save_extracted_text()
