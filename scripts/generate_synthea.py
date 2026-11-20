#!/usr/bin/env python3
"""Generate synthetic patients with Synthea. Output is fake data, safe to publish.

Usage:
    python scripts/generate_synthea.py --patients 1000
    python scripts/generate_synthea.py --patients 1000 --fhir   # also FHIR JSON (needed for the MongoDB step)

Requires Java 11 or newer. The Synthea jar is downloaded once into tools/.
"""
import argparse
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

JAR_URL = (
    "https://github.com/synthetichealth/synthea/releases/download/"
    "master-branch-latest/synthea-with-dependencies.jar"
)
ROOT = Path(__file__).resolve().parent.parent
JAR = ROOT / "tools" / "synthea-with-dependencies.jar"
OUT = ROOT / "data" / "raw"


def download_jar() -> None:
    JAR.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading Synthea (about 190 MB, one time) to {JAR} ...")
    tmp = JAR.with_suffix(".part")
    urllib.request.urlretrieve(JAR_URL, tmp)
    tmp.rename(JAR)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic patients with Synthea")
    parser.add_argument("--patients", type=int, default=1000, help="population size (default 1000)")
    parser.add_argument("--seed", type=int, default=42, help="random seed, same seed gives same data")
    parser.add_argument("--state", default="Massachusetts", help="US state to model")
    parser.add_argument("--fhir", action="store_true", help="also export FHIR JSON bundles")
    args = parser.parse_args()

    if shutil.which("java") is None:
        sys.exit("Java 11 or newer is required. Install it from https://adoptium.net, then run this again.")
    if not JAR.exists():
        download_jar()

    OUT.mkdir(parents=True, exist_ok=True)
    cmd = [
        "java", "-jar", str(JAR),
        "-p", str(args.patients),
        "-s", str(args.seed),
        "--exporter.csv.export=true",
        f"--exporter.fhir.export={'true' if args.fhir else 'false'}",
        f"--exporter.baseDirectory={OUT}",
        args.state,
    ]
    print("Running Synthea ...")
    subprocess.run(cmd, check=True)

    csv_dir = OUT / "csv"
    files = sorted(csv_dir.glob("*.csv")) if csv_dir.exists() else []
    print(f"\nDone. {len(files)} CSV files in {csv_dir}")
    print("Next: python scripts/load_raw.py, then cd dbt && dbt build")


if __name__ == "__main__":
    main()
