-- 02_metrics.sql — annual aggregates + quarterly display metrics.
-- Reads: quarterly (from sql/01, exposed via parquet in src/analysis.py).
-- Annual rows exist only for COMPLETE years (4 quarters): the partial current year
-- never enters an annual figure. Trailing-4-quarter windows live in src/analysis.py
-- (sensitivity) so this file stays a plain aggregation.
--
-- The 4-quarter window is ROWS BETWEEN 3 PRECEDING AND CURRENT ROW — 4 quarters by
-- row; sql/03_checks.sql asserts contiguity, so rows == consecutive quarters. The
-- sum is NULL until 4 rows exist: partial windows are never shown as sums (the old
-- RANGE window filled early rows with 2- and 3-quarter sums and the line chart
-- read them as a doubling that never happened).

CREATE OR REPLACE TABLE annual AS
SELECT
    year(quarter)                                        AS year,
    count(*)                                             AS quarters,
    sum(write_offs_sgd_m)                                AS write_offs_sgd_m,
    avg(rollover_sgd_m)                                  AS avg_rollover_sgd_m,
    sum(billings_sgd_m)                                  AS billings_sgd_m,
    avg(charge_off_rate_pct)                             AS rate_pct_avg_quarterly,
    100.0 * sum(write_offs_sgd_m) / avg(rollover_sgd_m)  AS rate_pct_recomputed
FROM quarterly
GROUP BY year(quarter)
HAVING count(*) = 4;

CREATE OR REPLACE TABLE quarterly_metrics AS
SELECT
    quarter,
    write_offs_sgd_m,
    CASE WHEN count(*) OVER w = 4
         THEN sum(write_offs_sgd_m) OVER w END           AS write_offs_4q_sgd_m,
    rollover_sgd_m,
    billings_sgd_m,
    charge_off_rate_pct
FROM quarterly
WINDOW w AS (ORDER BY quarter ROWS BETWEEN 3 PRECEDING AND CURRENT ROW);
