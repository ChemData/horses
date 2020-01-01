import random
import json
import os
import pandas as pd
import phenotype
import table_operations
import horse_functions
import race_functions
try:
    from game_parameters.local_constants import *
except ModuleNotFoundError:
    from game_parameters.constants import *


try:
    with(open(os.path.join(PARAMS_FOLDER, 'local_owner_names.json'), 'r')) as f:
        OWNER_NAMES = json.load(f)
except FileNotFoundError:
    with(open(os.path.join(PARAMS_FOLDER, 'owner_names.json'), 'r')) as f:
        OWNER_NAMES = json.load(f)


def pick_race_horses(owner_id, number):
    """Return a list of horse_ids to use in a race.

    Generally, fast horses will be selected. If the owner has fewer than number
    horses, it will return fewer.

    Args:
        owner_id (int): Owner_id of owner.
        number (int): How many horses to pick.

    Return:
        List. horse_ids to put in a race.
    """
    def calc_speed(x):
        return phenotype.speed(x['dna1'], x['dna2'])

    horses = horses_of(owner_id)
    if len(horses) == 0:
        return []
    horses['speed'] = horses.apply(calc_speed, axis=1)
    horses.sort_values(by='speed', inplace=True)

    return list(horses.iloc[:min(number, len(horses))]['horse_id'].values)


def horses_of(owner_id):
    """Return the living horses belonging to the specified owner.

    Args:
        owner_id (int): ID of the owner to find horses of.

    Return:
        pd.DataFrame. Containing all horse information.
    """
    command = f"SELECT * from horses where" \
        f" owner_id = {owner_id}" \
        f" and death_date is NULL"
    return table_operations.query_to_dataframe(command)


def add_money(owner_id, amount):
    """Add money to an owners account.

    Args:
        owner_id (int): ID of the owner.
        amount (float): Amount of money to add to that owner.

    Return:
        None
    """
    command = f"SET money = money + {amount} WHERE owner_id = {owner_id}"
    table_operations.update_value('owners', command)


def remove_money(owner_id, amount):
    """Remove the specified amount from an owner's account. Will raise an error if the
    owner has less than that amount to remove.
    Args:
        owner_id (int): ID of the owner.
        amount (float): Amount of money to remove from that owner.

    Return:
        None
    """
    cur_money = money(owner_id)
    if cur_money < amount:
        raise ValueError(f'{owner_id} only has {cur_money} and so {amount} cannot be'
                         f' removed from their account.')
    command = f"SET money = money - {amount} WHERE owner_id = {owner_id}"
    table_operations.update_value('owners', command)


def add_owner(money=0., name=None):
    """Create a new owner with the specified amount of money.

    Args:
        money (float): How much money the new owner has.
        name (str, None): Name to give to the owner. If None, will use a random name.

    Return:
        int. The owner_id of the new owner.

    """
    if name is None:
        name = random.choice(OWNER_NAMES)
    new_id = table_operations.insert_into_table('owners', {'money': money, 'name': name})
    return new_id


def money(owner_id):
    """Return how much money an owner has.

    Args:
        owner_id (int): ID of the owner of interest.

    Return:
         float. Money the owner has.
    """
    command = f"SELECT money FROM owners WHERE owner_id = {owner_id}"
    data = table_operations.query_to_dataframe(command)
    return data.iloc[0]['money']


def owner_list():
    """Return a list of owner_ids in the database."""
    owners = table_operations.get_primary_index('owners')
    # The key 1 is reserved for wild horses and won't be included in the list.
    try:
        owners.remove(1)
    except ValueError:
        pass
    return owners


def horse_value(horse_id, day):
    """Return the estimated value of a horse.

    Currently the value is purely based on the number of races the horse could be
    expected to run and how much they are expected to earn per race.

    Args:
        horse_id (int): ID of the horse to evaluate.
        day (datetime): Current day.

    Returns:
        float. How many dollars the horse is estimated to be worth.
    """
    current_age = horse_functions.age(horse_id, day).loc[0, 'age']
    max_age, _ = horse_functions.expected_race_life()
    remaining_life = max(0, max_age - current_age)

    expected_races = remaining_life/race_functions.races_per_day()
    return expected_races * horse_functions.expected_winnings(horse_id)


def evaluate_trade(owner_id, horse_id, amount, date, buy=True):
    """Call upon the owner to evaluate the proposed trade.

    Args:
        owner_id (int): ID of the owner.
        horse_id (int): ID of the horse that is being traded.
        amount (int): Amount of money proposed for the trade.
        date (datetime): Current day.
        buy (Bool): If True, owner is being offered a horse to buy.

    Return:
        String.
            'yes': offer is accepted.
            'no': offer is rejected.
            'soft no': offer is rejected because owner has too little money.
    """
    if buy and amount > money(owner_id):
        return 'soft no'
    horse = table_operations.get_rows('horses', horse_id).iloc[0]

    value = horse_value(horse_id, date)
    if horse['gender'] == 'F':
        value *= 1.5

    diff = value - amount

    if not buy:
        diff *= -1

    if diff > 0:
        return 'yes'
    else:
        return 'no'
