
from datetime import datetime, timedelta


def parse_date(val):
    """Parse any date value into a datetime object."""
    if not val or str(val).strip() in ('', 'nan', 'None', '[no field found]', 'NaT'):
        return None
    if isinstance(val, datetime):
        return val.replace(tzinfo=None) if val.tzinfo else val

    # Excel serial number e.g. 46372.0
    try:
        serial = float(str(val).strip())
        if 30000 < serial < 60000:
            return datetime(1899, 12, 30) + timedelta(days=serial)
    except Exception:
        pass

    s = str(val).strip()
    DATE_FORMATS = [
        '%Y-%m-%d',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%dT%H:%M:%S.%f',
        '%d/%m/%Y',
        '%m/%d/%Y',
        '%m/%d/%y',       # 4/22/26
        '%d/%m/%y',
        '%d-%m-%Y',
        '%d-%b-%Y',
        '%b %d, %Y',
        '%m/%d/%Y %H:%M',
        '%m/%d/%Y %H:%M:%S',
        '%Y/%m/%d',
    ]
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            pass
        try:
            return datetime.strptime(s[:10], fmt[:10])
        except Exception:
            pass

    return None


def days_between(d1, d2):
    """Return absolute difference in days between two dates."""
    if d1 and d2:
        return round(abs((d2 - d1).total_seconds()) / 86400, 1)
    return None
