import csv
import io
import random
import re
import struct
import zlib
from datetime import datetime
from pathlib import Path

import requests

BUCKET = "https://s3.amazonaws.com/baywheels-data"
OUT = Path(__file__).resolve().parent / "reports" / "hw07" / "cases"
SEED = 571
COLUMNS = ["ride_id", "rideable_type", "started_at", "ended_at", "start_station_name", "end_station_name"]


def month_files():
    listing = requests.get(BUCKET, timeout=60).text
    files = {}
    for key in re.findall(r"<Key>([^<]+\.zip)</Key>", listing):
        if key[:6].isdigit():
            files[key[:6]] = key
    return files


def first_rows(key, size=2_500_000):
    data = requests.get(f"{BUCKET}/{key}", headers={"Range": f"bytes=0-{size}"}, timeout=120).content
    name_len, extra_len = struct.unpack("<HH", data[26:30])
    text = zlib.decompressobj(-15).decompress(data[30 + name_len + extra_len:]).decode("utf-8", "ignore")
    lines = text.splitlines()[:-1]
    return list(csv.DictReader(io.StringIO("\n".join(lines))))


def minutes(row):
    start = datetime.fromisoformat(row["started_at"][:19])
    end = datetime.fromisoformat(row["ended_at"][:19])
    return (end - start).total_seconds() / 60


def build(name, months, per_month, keep):
    files = month_files()
    trips = []
    for month in months:
        rows = [r for r in first_rows(files[month]) if keep(r, minutes(r))]
        trips += random.sample(rows, per_month)
        print(f"{name} {month}: {len(rows)} candidate rows, took {per_month}")
    trips.sort(key=lambda r: r["started_at"])
    with open(OUT / f"{name}.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(trips)
    print(f"{name}: {len(trips)} trips written")


def month_range(first, last):
    year, month = int(first[:4]), int(first[4:])
    out = []
    while f"{year}{month:02d}" <= last:
        out.append(f"{year}{month:02d}")
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return out


if __name__ == "__main__":
    random.seed(SEED)
    OUT.mkdir(parents=True, exist_ok=True)
    build("bike_commuter_membership", month_range("202508", "202609"), 44, lambda r, m: 8 <= m <= 40)
    build("bike_occasional_payperuse", month_range("202309", "202609"), 14,
          lambda r, m: r["rideable_type"] == "classic_bike" and 1 <= m <= 5)
