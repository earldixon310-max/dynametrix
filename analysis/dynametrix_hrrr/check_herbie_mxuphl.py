"""
Quick herbie smoke test: fetch one HRRR cycle and confirm MXUPHL is accessible.

Run from repo root with the venv active:
    python analysis\\dynametrix_hrrr\\check_herbie_mxuphl.py

Expected output: a small xarray Dataset summary showing the MXUPHL field with
~1.9M grid cells (the HRRR CONUS grid). If this works, the full diagnostic's
load_hrrr_uh_probabilities will work.
"""
from datetime import datetime
from herbie import Herbie

# Pick a recent past HRRR cycle. March 1, 2026 00Z, 1-hour forecast.
init_time = datetime(2026, 3, 1, 0)
fxx = 1

print(f"Fetching HRRR init={init_time:%Y-%m-%d %H:%MZ} fxx={fxx} product=prs")
H = Herbie(
    init_time.strftime("%Y-%m-%d %H:%M"),
    model="hrrr",
    product="prs",
    fxx=fxx,
    verbose=True,
)
print(f"  Source URL: {H.grib}")
print(f"  Local file: {H.grib_source}")

print("\nSearching for MXUPHL 2-5 km AGL layer...")
ds = H.xarray(":MXUPHL:5000-2000 m above ground:")

print("\nDataset summary:")
print(ds)
print(f"\nData variables: {list(ds.data_vars)}")
print(f"Coordinates: {list(ds.coords)}")
print(f"Dimensions: {dict(ds.dims)}")

# Try to identify the UH variable.
import numpy as np
for name in ds.data_vars:
    arr = np.asarray(ds[name].values)
    print(f"\nVariable '{name}': shape={arr.shape}, "
          f"min={float(arr.min()):.3f}, max={float(arr.max()):.3f}, "
          f"mean={float(arr.mean()):.3f}")

print(f"\nLatitude range: {float(ds.latitude.min()):.3f} to {float(ds.latitude.max()):.3f}")
print(f"Longitude range: {float(ds.longitude.min()):.3f} to {float(ds.longitude.max()):.3f}")
print("\nOK")
