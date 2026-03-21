"""
Download script for London Static GTFS feed.
Source: UK Department for Transport - Bus Open Data Service (BODS)
URL: https://data.bus-data.dft.gov.uk/timetable/download/gtfs-file/london/
"""

import urllib.request
import os

URL = "https://data.bus-data.dft.gov.uk/timetable/download/gtfs-file/london/"
OUTPUT = os.path.join(os.path.dirname(__file__), "london_gtfs.zip")


def download():
    print(f"Downloading London GTFS from BODS...")
    urllib.request.urlretrieve(URL, OUTPUT)
    size_mb = os.path.getsize(OUTPUT) / (1024 * 1024)
    print(f"Saved to {OUTPUT} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    download()
