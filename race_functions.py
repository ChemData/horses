import datetime
import json
import numpy as np
import table_operations


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
    new_id = table_operations.insert_into_table('races', params)
    return new_id
