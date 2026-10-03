-- 05_checks.sql — validation queries for the staged `quarterly` table.
-- Each row: one check. src/build_dataset.py runs this and asserts all violations = 0.
-- Checks must survive regeneration: nothing here pins an exact row count;
-- the coverage floor is a lower bound, not an equality.

SELECT 'all six series per quarter' AS check_name,
       count(*) AS violations
FROM quarterly
WHERE principal_cardholders IS NULL OR supplementary_cardholders IS NULL
   OR billings_sgd_m IS NULL OR rollover_sgd_m IS NULL
   OR write_offs_sgd_m IS NULL OR charge_off_rate_pct IS NULL
UNION ALL SELECT 'no duplicate quarters',
       count(*) FROM (SELECT quarter FROM quarterly GROUP BY quarter HAVING count(*) > 1)
UNION ALL SELECT 'quarters contiguous',
       count(*) FROM (
           SELECT quarter, lag(quarter) OVER (ORDER BY quarter) AS prev FROM quarterly
       ) WHERE prev IS NOT NULL AND quarter <> CAST(prev + INTERVAL 1 QUARTER AS DATE)
UNION ALL SELECT 'quarters in range',
       count(*) FROM quarterly WHERE quarter < DATE '2014-10-01' OR quarter > CURRENT_DATE
UNION ALL SELECT 'coverage floor (>= 40 quarters)',
       CASE WHEN (SELECT count(*) FROM quarterly) >= 40 THEN 0 ELSE 1 END
UNION ALL SELECT 'card counts whole & positive',
       count(*) FROM quarterly
       WHERE principal_cardholders <= 0 OR supplementary_cardholders <= 0
          OR principal_cardholders <> round(principal_cardholders)
          OR supplementary_cardholders <> round(supplementary_cardholders)
UNION ALL SELECT 'money fields positive',
       count(*) FROM quarterly
       WHERE billings_sgd_m <= 0 OR rollover_sgd_m <= 0 OR write_offs_sgd_m <= 0
UNION ALL SELECT 'published rate in 0–50%',
       count(*) FROM quarterly WHERE charge_off_rate_pct < 0 OR charge_off_rate_pct > 50;
