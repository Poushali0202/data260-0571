import datetime

def notice_age_days(notice_date: datetime.datetime, today: datetime.datetime) -> int:
    """
    Calculate the number of whole days between a notice date and today.
    Raises ValueError if today is earlier than the notice date.
    """
    if today < notice_date:
        raise ValueError("Today cannot be earlier than the notice date")
    delta = today - notice_date
    return delta.days

def test_notice_age_days():
    assert notice_age_days(datetime.datetime(2023, 1, 1), datetime.datetime(2023, 1, 1)) == 0
    assert notice_age_days(datetime.datetime(2023, 1, 1), datetime.datetime(2023, 1, 2)) == 1
    assert notice_age_days(datetime.datetime(2023, 1, 1), datetime.datetime(2023, 1, 3)) == 2
    assert notice_age_days(datetime.datetime(2023, 1, 1), datetime.datetime(2023, 1, 1)) == 0
    try:
        notice_age_days(datetime.datetime(2023, 1, 2), datetime.datetime(2023, 1, 1))
    except ValueError:
        pass
    else:
        assert False, "Expected ValueError when today is earlier than notice date"
