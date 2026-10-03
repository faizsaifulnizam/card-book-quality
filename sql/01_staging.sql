-- 01_staging.sql — raw wide CSV -> per-quarter table `quarterly`.
-- Reads:  data/raw/credit-charge-cards-quarterly.csv (never modified)
-- Writes: table `quarterly`; parquet copy handled by src/build_dataset.py.
-- The raw file is wide: one row per series, one column per quarter label
-- ('20262Q' = 2026 Q2). Unpivot to long, parse the quarter, TRY_CAST values,
-- then pivot back to one row per quarter. The WHERE clause below mirrors the
-- exclusion rules counted in src/build_dataset.py (retained + excluded == raw cells).

CREATE OR REPLACE TABLE quarterly AS
WITH long AS (
    UNPIVOT (SELECT * FROM read_csv_auto('data/raw/credit-charge-cards-quarterly.csv'))
    ON COLUMNS(* EXCLUDE (DataSeries))
    INTO NAME q_label VALUE value
), parsed AS (
    SELECT
        DataSeries AS series,
        make_date(CAST(substr(q_label, 1, 4) AS INTEGER),
                  (CAST(substr(q_label, 5, 1) AS INTEGER) - 1) * 3 + 1, 1) AS quarter,
        TRY_CAST(value AS DOUBLE) AS v
    FROM long
    WHERE regexp_matches(q_label, '^[0-9]{4}[1-4]Q$')
      AND TRY_CAST(value AS DOUBLE) IS NOT NULL
      AND DataSeries IN ('Principal Cardholders', 'Supplementary Cardholders',
                         'Total Card Billings', 'Rollover Balance',
                         'Bad Debts Written Off', 'Charge-Off Rates')
)
SELECT
    quarter,
    CAST(max(CASE WHEN series = 'Principal Cardholders' THEN v END) AS BIGINT)     AS principal_cardholders,
    CAST(max(CASE WHEN series = 'Supplementary Cardholders' THEN v END) AS BIGINT) AS supplementary_cardholders,
    max(CASE WHEN series = 'Total Card Billings' THEN v END)      AS billings_sgd_m,
    max(CASE WHEN series = 'Rollover Balance' THEN v END)         AS rollover_sgd_m,
    max(CASE WHEN series = 'Bad Debts Written Off' THEN v END)    AS write_offs_sgd_m,
    max(CASE WHEN series = 'Charge-Off Rates' THEN v END)         AS charge_off_rate_pct
FROM parsed
GROUP BY quarter
ORDER BY quarter;
