select
    ts::timestamptz as ts,
    meter_id::text as meter_id,
    city::text as city,
    power_kw::numeric as power_kw,
    voltage_v::numeric as voltage_v,
    time_bucket('5 minutes', ts) as bucket
from {{ source('raw', 'meter_telemetry') }}
