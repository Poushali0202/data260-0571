# HW4 measurements

Machine: Intel Core i5-1135G7, 15.8 GB RAM, Windows 11 Home, CPU only. MySQL 8.0.46 in the
Docker container `s0571-mysql` (port 3307), FastAPI on port 8571, both on the same laptop.
Console output with timestamps: `RUN_LOG.txt`.

## Part 3: N+1 measurement

`python measure_n_plus_one.py` logs in once, then for every page size (10, 50, 200) and version
(naive, fixed) sends 2 warm-up requests followed by 30 measured requests to
`GET /api/notices/{version}?page_size=N` on `127.0.0.1:8571`. Latency is the wall-clock time of
the whole HTTP request measured in the client with `time.perf_counter()`. The SQL statement count
is reported by the endpoint itself: a `before_cursor_execute` listener on the engine increments a
per-request counter that the endpoint starts before its first query and reads after it has built
the response. The session lookup that every protected route runs before the endpoint body is not
inside the count; the MySQL general log in `RUN_LOG.txt` shows it as one extra `SELECT sessions`
statement per request for both versions. All 180 measured requests are in
`raw/n_plus_one_requests.csv`; `raw/n_plus_one_summary.json` holds the percentiles below
(`numpy.percentile`, linear interpolation over the 30 samples).

The seeded data has 5,000 notices and 200 lots attached to the 200 newest notices (ids 4801 to
5000), and both list endpoints return the newest notices first, so a page of 10 carries 9 lots,
a page of 50 carries 56 and a page of 200 carries all 200.

| Page size | Version | SQL stmts/req | p50 (ms) | p95 (ms) | p99 (ms) |
|---|---|---|---|---|---|
| 10 | naive | 11 | 23.76 | 29.21 | 72.06 |
| 10 | fixed | 2 | 10.12 | 12.04 | 12.81 |
| 50 | naive | 51 | 92.52 | 149.12 | 160.95 |
| 50 | fixed | 2 | 13.69 | 19.28 | 19.65 |
| 200 | naive | 201 | 647.48 | 870.04 | 1050.93 |
| 200 | fixed | 2 | 32.29 | 61.64 | 81.70 |

Speed-up of the fixed version (naive divided by fixed):

| Page size | p50 naive / fixed | p95 naive / fixed | ms saved per request (p50) | Extra statements removed |
|---|---|---|---|---|
| 10 | 2.35x | 2.43x | 13.64 | 9 |
| 50 | 6.76x | 7.73x | 78.83 | 49 |
| 200 | 20.05x | 14.12x | 615.19 | 199 |

The naive endpoint issues one `SELECT ... FROM notice_lots WHERE notice_id = %s` per notice on
the page, so its cost is a fixed part (session lookup, the notices query, JSON encoding) plus
about 1.5 ms per notice at page sizes 10 and 50 and about 3 ms per notice at 200 (each round trip
goes through the Docker port mapping and builds ORM objects). The fixed version replaces the N
statements with one `SELECT ... FROM notice_lots WHERE notice_id IN (...)`, whose cost only grows
with the number of rows returned. The fixed part is the same for both, so at page size 10 it
still dominates and the ratio is small; at 200 the naive version spends almost all of its time
in the 200 extra round trips and the ratio reaches 20x.

## Part 3 step 8: one index

Index: `CREATE INDEX ix_grocery_notices_notice_source ON grocery_notices (notice_source)`
(`migrations/hw04_add_index.sql`). Query:
`SELECT id, product_name, notice_source FROM grocery_notices WHERE notice_source = 'FDA recall bulletin' ORDER BY id`.

| | Before the index | After the index |
|---|---|---|
| `type` | index (full scan of the PRIMARY index) | ref |
| `key` | PRIMARY | ix_grocery_notices_notice_source |
| `rows` | 5158 | 183 |
| `filtered` | 10.00 | 100.00 |
| `Extra` | Using where | NULL |
| EXPLAIN ANALYZE | Filter over an index scan: 5000 rows read, 183 kept, cost 522, 2.16 ms | Index lookup: 183 rows read, cost 37, 0.593 ms |

Without the index MySQL has no way to find the rows for one source except reading the whole
table; it walks the primary key (which also delivers the `ORDER BY id` order) and applies the
`WHERE` to all 5,000 rows. With the index it jumps to the 183 matching entries directly, the
estimate matches the real row count, and because an InnoDB secondary index stores the primary key
next to each entry the rows already come out in `id` order, so no filesort is needed either.
