"""
Download script for London Static GTFS feed.
Source: UK Department for Transport - Bus Open Data Service (BODS)
URL: https://data.bus-data.dft.gov.uk/timetable/download/gtfs-file/london/
"""

import urllib.request
import os
from zipfile import ZipFile

URL = "https://data.bus-data.dft.gov.uk/timetable/download/gtfs-file/london/"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
OUTPUT = os.path.join(BASE_DIR, "data/raw/london_gtfs.zip")
EXTRACTED = os.path.join(BASE_DIR, "data/raw/london_gtfs")


def download():
    print(f"Downloading London GTFS from BODS...")
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    urllib.request.urlretrieve(URL, OUTPUT)
    size_mb = os.path.getsize(OUTPUT) / (1024 * 1024)
    print(f"Saved to {OUTPUT} ({size_mb:.1f} MB)")

    with ZipFile(OUTPUT, "r") as zObject:
        zObject.extractall(path=EXTRACTED)
    print(f"Extracted to {EXTRACTED}")

if __name__ == "__main__":
    download()
