select
    ts::timestamptz as ts,
    region::text as region,
    load_mw::numeric as load_mw,
    capacity_mw::numeric as capacity_mw,
    wind_mw::numeric as wind_mw,
    solar_mw::numeric as solar_mw,
    load_mw / nullif(capacity_mw, 0) as strain_ratio
from {{ source('raw', 'grid_conditions') }}
