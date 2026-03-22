"""
Download script for TfL Annual Report and Statement of Accounts 2024/25.
Source: Transport for London (TfL) official publications
URL: https://content.tfl.gov.uk/tfl-annual-report-and-statement-of-accounts-2024-25.pdf
"""

import urllib.request
import os

URL = "https://content.tfl.gov.uk/tfl-annual-report-and-statement-of-accounts-2024-25.pdf"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
OUTPUT = os.path.join(BASE_DIR, "data/raw/london_gtfs.zip")

def download():
    print(f"Downloading TfL Annual Report 2024/25...")
    urllib.request.urlretrieve(URL, OUTPUT)
    size_mb = os.path.getsize(OUTPUT) / (1024 * 1024)
    print(f"Saved to {OUTPUT} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    download()
