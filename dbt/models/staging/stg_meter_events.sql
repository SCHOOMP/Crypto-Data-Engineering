select
    ts::timestamptz as ts,
    meter_id::text as meter_id,
    event_type::text as event_type,
    detail::text as detail
from {{ source('raw', 'meter_events') }}
