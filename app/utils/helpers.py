from datetime import datetime, time, timedelta, timezone
from typing import List, Tuple


def convert_time_utc_with_tz(time_str: str, tz: str) -> time:
    """
    Convert a time string to UTC with the given timezone.
    
    Args:
        time (str): The time string to convert. "09:00" in 24 hour format
        tz (str): The timezone to use for conversion. "UTC+1"
        
    Returns:
        datetime: The converted UTC datetime object.
    """
    hours = int(tz)
    local_offset = timezone(timedelta(hours=hours))
    local_dt = datetime.strptime(time_str, "%H:%M")
    local_dt = local_dt.replace(tzinfo=local_offset)
    utc_dt = local_dt.astimezone(timezone.utc)

    return utc_dt.time()


from datetime import datetime, timedelta, timezone
from typing import List, Tuple

def convert_utc_days_and_time(days: List[str], time_str: str, tz: str) -> Tuple[List[str], str]:
    """
    Convert a list of days and a time string to UTC with the given timezone.
    
    Args:
        days (List[str]): The list of days to convert. ["Monday", "Tuesday"]
        time_str (str): The time string to convert. "09:00" in 24-hour format.
        tz (str): The timezone to use for conversion. Example: "+1", "-10"
        
    Returns:
        Tuple[List[str], str]: A tuple containing the converted list of UTC days and the UTC time string.
    """
    weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    utc_days = []

    # Parse timezone offset
    hours = int(tz)
    local_tz = timezone(timedelta(hours=hours))

    # Use the first day as a reference to get UTC time
    first_day_index = weekdays.index(days[0])
    ref_date = datetime(2025, 1, 6 + first_day_index)  # Jan 6, 2025 is a Monday

    local_dt = datetime.strptime(time_str, "%H:%M").replace(
        year=ref_date.year, month=ref_date.month, day=ref_date.day, tzinfo=local_tz
    )
    utc_dt = local_dt.astimezone(timezone.utc)
    utc_time = utc_dt.strftime("%H:%M")

    # Convert each day with same local time
    for day in days:
        day_index = weekdays.index(day)
        ref_date = datetime(2025, 1, 6 + day_index)
        local_dt = datetime.strptime(time_str, "%H:%M").replace(
            year=ref_date.year, month=ref_date.month, day=ref_date.day, tzinfo=local_tz
        )
        utc_dt = local_dt.astimezone(timezone.utc)
        utc_day = weekdays[utc_dt.weekday()]
        utc_days.append(utc_day)

    return utc_days, utc_time
