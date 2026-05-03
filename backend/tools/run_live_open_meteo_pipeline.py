"""
STUB engine file.

Replace with the real `tools/run_live_open_meteo_pipeline.py` from the existing
engine. This stub just writes a few synthetic rows so the SaaS scaffold can
exercise the full call chain.

Expected CLI:
    python run_live_open_meteo_pipeline.py --lat <f> --lon <f> --out <path>
"""
import argparse
import csv
import sys
from datetime import datetime, timedelta, timezone


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lat", type=float, required=True)
    ap.add_argument("--lon", type=float, required=True)
    ap.add_argument("--out", type=str, required=True)
    args = ap.parse_args()

    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    rows = []
    for i in range(24):
        rows.append({
            "observed_at": (now - timedelta(hours=23 - i)).isoformat(),
            "lat": args.lat,
            "lon": args.lon,
            "temperature_c": 5 + i % 10,
            "wind_kph": 10 + (i % 7) * 2,
            "pressure_hpa": 1010 - (i % 5),
        })
    with open(args.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} rows -> {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
