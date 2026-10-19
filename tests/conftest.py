"""A tiny closed_system-shaped DuckDB so the build runs hermetically: one Ramsey zip, six homes, five sales."""
import sys
from pathlib import Path

import duckdb
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

HOMES = [  # pk, pin, emv_2025, emv_2024, tax, sf, yb, lat, lon, house, street, homestead, own_sale
    ("ramsey:1", "1", 400_000, 360_000, 5_200, 1500, 1950, 44.9500, -93.1000, "100", "ELM ST", "Yes", None),
    ("ramsey:2", "2", 300_000, 290_000, 3_900, 1520, 1952, 44.9510, -93.1000, "102", "ELM ST", "Yes", 305_000),
    ("ramsey:3", "3", 310_000, 300_000, 4_000, 1480, 1949, 44.9520, -93.1000, "104", "ELM ST", "No", 296_000),
    ("ramsey:4", "4", 305_000, 295_000, 3_950, 1550, 1955, 44.9530, -93.1000, "106", "ELM ST", "Yes", 310_000),
    ("ramsey:5", "5", 295_000, 280_000, 3_800, 1450, 1948, 44.9540, -93.1000, "108", "ELM ST", "Yes", 290_000),
    ("ramsey:6", "6", 320_000, 300_000, 4_100, 1600, 1960, 44.9550, -93.1000, "901", "OAK AVE", "Yes", 320_000),
]
SALES = [("ramsey:2", "2025-06-01", 305_000), ("ramsey:3", "2025-03-15", 296_000), ("ramsey:4", "2024-11-01", 310_000),
         ("ramsey:5", "2025-08-01", 290_000), ("ramsey:6", "2025-01-10", 320_000), ("ramsey:6", "2019-01-10", 200_000),
         ("ramsey:5", "2025-09-01", 10_000)]


@pytest.fixture(scope="session")
def fixture_db(tmp_path_factory):
    p = tmp_path_factory.mktemp("db") / "closed.duckdb"
    con = duckdb.connect(str(p))
    con.execute("""create table parcel_snapshot(vintage varchar, as_of date, parcel_key varchar, county varchar, pin varchar,
        emv_total double, total_tax double, mkt_year int, useclass1 varchar, homestead varchar, year_built int, fin_sq_ft double,
        sale_date date, sale_value double, anumber varchar, street varchar, city varchar, zip varchar, lat double, lon double, attrs json)""")
    con.execute("create table parcel(parcel_key varchar, county varchar, lat double, lon double)")
    con.execute("create table sale(parcel_key varchar, sale_date date, sale_value double)")
    con.execute("create table address_index(house varchar, street varchar, city varchar, zip varchar, parcel_key varchar)")
    for pk, pin, emv, prior, tax, sf, yb, lat, lon, house, street, hs, own in HOMES:
        own_d = "2025-06-01" if own else None
        con.execute("insert into parcel_snapshot values ('metrogis_current', DATE '2026-09-24', ?, 'ramsey', ?, ?, ?, 2025, '1A/1B/4BB RESIDENTIAL SINGLE UNIT', ?, ?, ?, ?, ?, ?, ?, 'ST PAUL', '55104', ?, ?, '{}')",
                    [pk, pin, emv, tax, hs, yb, sf, own_d, own, house, street, lat, lon])
        con.execute("insert into parcel_snapshot values ('metrogis_2025', DATE '2025-12-31', ?, 'ramsey', ?, ?, ?, 2024, '1A/1B/4BB RESIDENTIAL SINGLE UNIT', ?, ?, ?, NULL, NULL, ?, ?, 'ST PAUL', '55104', ?, ?, '{}')",
                    [pk, pin, prior, tax, hs, yb, sf, house, street, lat, lon])
        con.execute("insert into parcel values (?, 'ramsey', ?, ?)", [pk, lat, lon])
        con.execute("insert into address_index values (?, ?, 'ST PAUL', '55104', ?)", [house, street, pk])
    for pk, d, v in SALES:
        con.execute("insert into sale values (?, ?, ?)", [pk, d, v])
    con.close()
    return p


@pytest.fixture(scope="session")
def built(fixture_db, tmp_path_factory):
    import build
    from datetime import date
    out = tmp_path_factory.mktemp("out")
    meta = build.build(fixture_db, out, ["ramsey"], 0, date(2026, 10, 19))
    return out, meta
