from datetime import datetime, time, timedelta, timezone

def convert_time_utc_with_tz(time_str:str, tz:str) -> time:
    """
    Convert a time string to UTC with the given timezone.
    
    Args:
        time (str): The time string to convert. "09:00"
        tz (str): The timezone to use for conversion. "UTC+1"
        
    Returns:
        datetime: The converted UTC datetime object.
    """
    hours = int(tz.split("+")[1])
    local_offset = timezone(timedelta(hours=hours))
    local_dt = datetime.strptime(time_str, "%H:%M")
    local_dt = local_dt.replace(tzinfo=local_offset)
    utc_dt = local_dt.astimezone(timezone.utc)

    return utc_dt.time()