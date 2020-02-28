from pandas import to_datetime, datetime
import table_operations as to
import game_parameters.constants as C


def put_events_on_calendar(year):
    """
    Take all annual events and place them into the calendar table.

    Args:
        year (int): The year to load events for.

    Returns:
        None.
    """
    for event, params in C.EVENTS.items():
        date = as_sql_date(datetime(year, params['date'][0], params['date'][1]))
        cmd = "INSERT OR REPLACE INTO calendar ('date', 'type', 'name') VALUES (?, ?, ?)"
        to.db.execute(cmd, [date, params['type'], event])
    to.db.commit()


def as_sql_date(date):
    """Return a date in the form 'YYYY-MM-DD'"""
    date = to_datetime(date)
    return str(date.date())