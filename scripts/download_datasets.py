"""
Standalone script to download datasets.
Usage: python scripts/download_datasets.py [--phase 1]
"""

import sys
from kryntis.datasets.downloader import DatasetDownloader

if __name__ == "__main__":
    phase = 1
    if len(sys.argv) > 2 and sys.argv[1] == "--phase":
        phase = int(sys.argv[2])
    print(f"Downloading Phase {phase} datasets...")
    downloader = DatasetDownloader()
    downloader.download_all(phase=phase)
    print("Download completed.")
