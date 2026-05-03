"""Tests for the SPC storm-reports parser.

Pure parser tests — no HTTP, no database. The parser is a string-in,
list-of-dicts-out function and that's all we test here.
"""

from datetime import date, timezone

from app.services.storm_reports import parse_spc_csv


SAMPLE_TORNADO_CSV = """Time,F_Scale,Location,County,State,Lat,Lon,Comments
1430,EF1,GREENVILLE,GREENVILLE,SC,34.85,-82.39,"Damage to multiple structures"
1525,EF0,GASTONIA,GASTON,NC,35.27,-81.18,"Brief touchdown"
1730,UNK,RALEIGH,WAKE,NC,35.78,-78.64,"Funnel reported by spotter"
"""

SAMPLE_HAIL_CSV = """Time,Size,Location,County,State,Lat,Lon,Comments
1430,1.50,FORT WORTH,TARRANT,TX,32.75,-97.33,"Quarter-size hail"
1500,2.00,DALLAS,DALLAS,TX,32.78,-96.80,"Hen-egg hail"
"""

SAMPLE_WIND_CSV = """Time,Speed,Location,County,State,Lat,Lon,Comments
1830,75,DENVER,DENVER,CO,39.74,-104.99,"Tree down on roadway"
1845,UNK,AURORA,ARAPAHOE,CO,39.73,-104.83,"Damage reports"
"""


def test_parser_extracts_tornado_rows():
    events = parse_spc_csv(SAMPLE_TORNADO_CSV, "tornado", date(2026, 4, 27))
    assert len(events) == 3


def test_parser_extracts_hail_rows():
    events = parse_spc_csv(SAMPLE_HAIL_CSV, "hail", date(2026, 4, 27))
    assert len(events) == 2


def test_parser_extracts_wind_rows():
    events = parse_spc_csv(SAMPLE_WIND_CSV, "wind", date(2026, 4, 27))
    assert len(events) == 2


def test_parser_normalizes_event_at_to_utc():
    events = parse_spc_csv(SAMPLE_TORNADO_CSV, "tornado", date(2026, 4, 27))
    first = events[0]
    assert first["event_at"].tzinfo == timezone.utc
    assert first["event_at"].hour == 14
    assert first["event_at"].minute == 30


def test_parser_captures_severity_from_correct_field():
    tornado_events = parse_spc_csv(SAMPLE_TORNADO_CSV, "tornado", date(2026, 4, 27))
    assert tornado_events[0]["severity"] == "EF1"
    assert tornado_events[2]["severity"] == "UNK"

    hail_events = parse_spc_csv(SAMPLE_HAIL_CSV, "hail", date(2026, 4, 27))
    assert hail_events[0]["severity"] == "1.50"

    wind_events = parse_spc_csv(SAMPLE_WIND_CSV, "wind", date(2026, 4, 27))
    assert wind_events[0]["severity"] == "75"


def test_parser_extracts_lat_lon_as_floats():
    events = parse_spc_csv(SAMPLE_TORNADO_CSV, "tornado", date(2026, 4, 27))
    e = events[0]
    assert isinstance(e["latitude"], float)
    assert isinstance(e["longitude"], float)
    assert e["latitude"] == 34.85
    assert e["longitude"] == -82.39


def test_parser_creates_stable_source_event_id():
    # Same input should produce identical source_event_id, so re-ingestion
    # is idempotent against the unique constraint.
    a = parse_spc_csv(SAMPLE_TORNADO_CSV, "tornado", date(2026, 4, 27))
    b = parse_spc_csv(SAMPLE_TORNADO_CSV, "tornado", date(2026, 4, 27))
    assert a[0]["source_event_id"] == b[0]["source_event_id"]


def test_parser_skips_empty_csv():
    assert parse_spc_csv("", "tornado", date(2026, 4, 27)) == []


def test_parser_skips_only_header():
    text = "Time,F_Scale,Location,County,State,Lat,Lon,Comments\n"
    assert parse_spc_csv(text, "tornado", date(2026, 4, 27)) == []


def test_parser_skips_rows_missing_coordinates():
    text = """Time,F_Scale,Location,County,State,Lat,Lon,Comments
1430,EF0,SOMEWHERE,SOMECOUNTY,SC,,,No coords
1500,EF1,REALPLACE,REALCOUNTY,NC,35.0,-80.0,Has coords
"""
    events = parse_spc_csv(text, "tornado", date(2026, 4, 27))
    assert len(events) == 1
    assert events[0]["severity"] == "EF1"


def test_parser_handles_malformed_time():
    text = """Time,F_Scale,Location,County,State,Lat,Lon,Comments
abcd,EF0,BAD,SOMECOUNTY,SC,34.85,-82.39,Bad time
1430,EF1,OK,SOMECOUNTY,SC,34.85,-82.39,OK row
"""
    events = parse_spc_csv(text, "tornado", date(2026, 4, 27))
    assert len(events) == 1
    assert events[0]["severity"] == "EF1"


def test_parser_pads_short_time_strings():
    # SPC sometimes emits "732" instead of "0732" (leading-zero stripped).
    text = """Time,F_Scale,Location,County,State,Lat,Lon,Comments
732,EF0,EARLY,SOMECOUNTY,SC,34.85,-82.39,Early morning
"""
    events = parse_spc_csv(text, "tornado", date(2026, 4, 27))
    assert len(events) == 1
    assert events[0]["event_at"].hour == 7
    assert events[0]["event_at"].minute == 32


def test_parser_marks_source_as_spc():
    events = parse_spc_csv(SAMPLE_TORNADO_CSV, "tornado", date(2026, 4, 27))
    assert all(e["source"] == "SPC" for e in events)


def test_parser_preserves_raw_row_for_debugging():
    events = parse_spc_csv(SAMPLE_TORNADO_CSV, "tornado", date(2026, 4, 27))
    assert "Comments" in events[0]["raw"]
    assert events[0]["raw"]["Comments"] == "Damage to multiple structures"