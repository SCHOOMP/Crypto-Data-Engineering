
-- 1. Sanity check: confirms the epoch is in seconds (min should land in 2012, max ~now).
SELECT to_timestamp(min(ts_epoch)) AS earliest,
       to_timestamp(max(ts_epoch)) AS latest
FROM bitcoin_raw;


-- 2. Exploratory aggregation: previews 50 hourly rows without persisting, for eyeballing.
SELECT
    'BTC' AS symbol,
    date_trunc('hour', to_timestamp(ts_epoch), 'UTC') AS hour,
    (array_agg(open  ORDER BY ts_epoch)      FILTER (WHERE open  IS NOT NULL))[1] AS open,
    max(high)   AS high,
    min(low)    AS low,
    (array_agg(close ORDER BY ts_epoch DESC) FILTER (WHERE close IS NOT NULL))[1] AS close,
    sum(volume) AS volume,
    count(*) FILTER (WHERE open IS NOT NULL)  AS trade_minutes
FROM bitcoin_raw
GROUP BY 1, 2
ORDER BY hour
LIMIT 50;


-- 3. Creates the hourly table with explicit types and a (symbol, hour) primary key that enforces the grain.
CREATE TABLE bitcoin_hourly (
    symbol        TEXT         NOT NULL,
    hour          TIMESTAMPTZ  NOT NULL,
    open          NUMERIC(18,8),
    high          NUMERIC(18,8),
    low           NUMERIC(18,8),
    close         NUMERIC(18,8),
    volume        NUMERIC(24,8),
    trade_minutes SMALLINT     NOT NULL,
    PRIMARY KEY (symbol, hour)
);


-- 4. Idempotent load: wipes only bitcoin_hourly and rebuilds it from raw, omitting zero-trade hours.
TRUNCATE bitcoin_hourly;
INSERT INTO bitcoin_hourly (symbol, hour, open, high, low, close, volume, trade_minutes)
SELECT
    'BTC' AS symbol,
    date_trunc('hour', to_timestamp(ts_epoch), 'UTC') AS hour,
    (array_agg(open  ORDER BY ts_epoch)      FILTER (WHERE open  IS NOT NULL))[1] AS open,
    max(high)   AS high,
    min(low)    AS low,
    (array_agg(close ORDER BY ts_epoch DESC) FILTER (WHERE close IS NOT NULL))[1] AS close,
    sum(volume) AS volume,
    count(*) FILTER (WHERE open IS NOT NULL)  AS trade_minutes
FROM bitcoin_raw
GROUP BY 1, 2
HAVING count(*) FILTER (WHERE open IS NOT NULL) > 0;


-- 5. Spot-check: pulls the raw minutes inside one hour to hand-verify open=first minute and close=last.
SELECT to_timestamp(ts_epoch) AT TIME ZONE 'UTC' AS minute,
       open, high, low, close, volume
FROM bitcoin_raw
WHERE to_timestamp(ts_epoch) AT TIME ZONE 'UTC' >= '2021-01-01 14:00'
  AND to_timestamp(ts_epoch) AT TIME ZONE 'UTC' <  '2021-01-01 15:00'
ORDER BY minute;