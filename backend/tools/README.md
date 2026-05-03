# tools/ — engine layer

This folder is where the **existing** Dynametrix structural detection engine lives.
Drop the real files here — the SaaS service layer in `backend/app/services/engine_service.py`
calls them by their documented signatures.

Expected files (per spec section 11):

- `mcc_early_warning_app.py`              — current Streamlit prototype dashboard
- `run_live_open_meteo_pipeline.py`       — fetches & enriches live weather feed
- `train_weather_commitment_calibrator.py` — trains AI-assisted calibration layer
- `weather_commitment_calibrated.csv`     — calibrated output (consumed by dashboard)
- `client_enriched_weather.csv`           — enriched weather feed
- `ci_structural_signatures_app.csv`      — raw MCC/CI structural signature output
- `ci_structural_signatures_app_nj_demo.csv` — historical demo signatures
- `hourly_weather_nj_2026_01_22_26_enriched.csv` — historical NJ storm demo
- `alerts.py`                             — alert helper functions

Until the real files are in place, the stubs in this folder let the SaaS scaffold
boot end-to-end (the seed script + dashboard will work; the dashboard will just be empty).

See `docs/ENGINE_INTEGRATION.md` for the full I/O contract per script.
