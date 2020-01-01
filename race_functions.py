import datetime
import json
import numpy as np
import table_operations as to


def add_race(start_time, distance, purse):
    """Add a new race to the database.

    Args:
        start_time (datetime): Date and time of the start of the race.
        distance (float): Distance (in meters) of the race.
        purse (tuple): Amount of money the winners received.

    Returns:
          int. ID of the race.
    """
    params = {'date': start_time, 'distance': distance, 'total_purse': sum(purse)}
    new_id = to.insert_into_table('races', params)
    return new_id


def races_per_day():
    """Return the average number of races per day that have been run.
    """

    races = to.query_to_dataframe("SELECT date FROM races")

    return len(races)/\
           ((races['date'].values[-1] - races['date'].values[0])/np.timedelta64(1, 'D')+1)
