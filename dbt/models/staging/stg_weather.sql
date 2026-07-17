select
    ts::timestamptz as ts,
    city::text as city,
    temperature_c::numeric as temperature_c,
    humidity_pct::numeric as humidity_pct,
    wind_speed_kmh::numeric as wind_speed_kmh
from {{ source('raw', 'weather') }}
