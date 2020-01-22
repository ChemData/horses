import os
import datetime
import json
import random
import numpy as np
import pandas as pd
import table_operations
import genetics
import phenotype
from game_parameters.constants import *

try:
    with(open(os.path.join(PARAMS_FOLDER, 'local_horse_names.json'), 'r')) as f:
        HORSE_NAMES = json.load(f)
except FileNotFoundError:
    with(open(os.path.join(PARAMS_FOLDER, 'horse_names.json'), 'r')) as f:
        HORSE_NAMES = json.load(f)

MALE_NAMES = HORSE_NAMES['male'] + HORSE_NAMES['unisex']
FEMALE_NAMES = HORSE_NAMES['female'] + HORSE_NAMES['unisex']


def horse_title(gender, age):
    """Return the title of a horse based on its age and gender."""
    title = ''
    if age < 365:
        title += 'weanling '
    elif age < 365*2:
        title += 'yearling '

    if gender == 'M':
        if age < 365*4:
            title += 'colt'
        else:
            title += 'stallion'
    else:
        if age < 365*4:
            title += 'filly'
        else:
            title += 'mare'
    return title


def make_random_horses(number, max_date):
    for i in range(number):
        z = make_random_horse(max_date)
        add_horse(z)


def make_random_horse(max_date):
    """Add a new random horse to the database."""

    output = {}
    age = int(np.random.random_integers(1, round(LIFE_MEAN*.5)))
    output['birth_date'] = str(max_date - datetime.timedelta(age))
    death = round(np.random.normal(LIFE_MEAN, LIFE_STD))
    output['expected_death'] = str(max_date - datetime.timedelta(age) + datetime.timedelta(death))
    output['gender'] = np.random.choice(['M', 'F'])
    if output['gender'] == 'M':
        output['name'] = np.random.choice(HORSE_NAMES['male']+HORSE_NAMES['unisex'])
    else:
        output['name'] = np.random.choice(HORSE_NAMES['female'] + HORSE_NAMES['unisex'])
    output['owner_id'] = 1
    output['dna1'] = genetics.random_chromosome()
    output['dna2'] = genetics.random_chromosome()

    return output


def add_horse(horse_params):
    """Add a horse to the table."""
    new_id = table_operations.insert_into_table('horses', horse_params)
    phenotype.calc_properties(new_id)
    return new_id


def trade_horse(horse_id, new_owner_id):
    """Transfer owndership of a horse from one owner to another."""
    command = f"SET owner_id = {new_owner_id} WHERE horse_id = {horse_id}"
    table_operations.update_value('horses', command)


def horse_sex(horse1, horse2, date):
    """Make two horses have sex.

    One horse must be male, another female. The female cannot be pregnant. Both horses
    must be sexually mature.
    Args:
        horse1 (int): ID of the first horse.
        horse2 (int): ID of the second horse.
        date (datetime.date): Day on which this is occurring.
    """
    data = table_operations.get_rows('horses', [horse1, horse2])
    data.set_index('horse_id', inplace=True)

    if data.loc[horse1, 'gender'] == data.loc[horse2, 'gender']:
        raise WrongGender('You need a dam and sire to make babies happen.')

    if (date - data.loc[horse1, 'birth_date']).days < SEXUAL_MATURITY:
        raise WrongAge(f'{horse1} is too young to have sex.')

    if (date - data.loc[horse2, 'birth_date']).days < SEXUAL_MATURITY:
        raise WrongAge(f'{horse2} is too young to have sex.')

    lady_horse = data[data['gender'] == 'F'].iloc[0]
    if lady_horse['due_date'] is not None and not pd.isna(lady_horse['due_date']):
        raise PregnancyIssue(f'{lady_horse.name} is already pregnant.')
    man_horse = data[data['gender'] == 'M'].iloc[0]

    num_days = round(np.random.normal(GESTATION_MEAN, GESTATION_STD))
    due_date = date + datetime.timedelta(num_days)
    command = f"SET due_date = '{str(due_date)}' WHERE horse_id = {lady_horse.name}"
    table_operations.update_value('horses', command)

    command = f"SET impregnated_by = '{man_horse.name}' WHERE horse_id = {lady_horse.name}"
    table_operations.update_value('horses', command)


def give_birth(horse, date, name=None):
    """Make a horse give birth to a pony.

    Args:
        horse (int): ID of the pregnant horse.
        date (datetime): Date of birth.
        name (str or None): Name of the new horse. If None, will use a random name
            appropriate to the foal's sex.

    """
    dam = table_operations.get_rows('horses', horse).iloc[0]

    if dam['impregnated_by'] is None:
        raise PregnancyIssue(f'{horse} is not pregnant and so cannot give birth.')

    sire = table_operations.get_rows('horses', dam['impregnated_by']).iloc[0]

    foal = make_random_horse(date)
    foal['dam'] = dam['horse_id']
    foal['sire'] = sire['horse_id']
    foal['owner_id'] = dam['owner_id']
    foal['birth_date'] = str(date)
    foal['expected_death'] = str(date + datetime.timedelta(
        round(np.random.normal(LIFE_MEAN, LIFE_STD))))
    if name is not None:
        foal['name'] = name
    else:
        if foal['gender'] == 'F':
            foal['name'] = np.random.choice(FEMALE_NAMES, 1)[0]
        else:
            foal['name'] = np.random.choice(MALE_NAMES, 1)[0]

    mix_genomes(dam, sire, foal)
    new_id = add_horse(foal)

    command = f"SET impregnated_by = NULL WHERE horse_id = {horse}"
    table_operations.update_value('horses', command)

    command = f"SET due_date = NULL WHERE horse_id = {horse}"
    table_operations.update_value('horses', command)

    return new_id


def mix_genomes(dam, sire, foal):
    """Combine the genomes of dam and sire to create the foal's genome.

    Args:
        dam (pd.Series): dam data.
        sire (pd.Series): sire data.
        foal (dict): Data from the foal.

    Returns:
        Nothing. Just updates the foal dict.
    """

    foal['dna1'] = genetics.mix_chromosomes(dam['dna1'], dam['dna2'])
    foal['dna2'] = genetics.mix_chromosomes(sire['dna1'], sire['dna2'])


def pedigree(horse, max_depth=3, base_depth=0):
    """Return the ancestors of the specified horse.

    Args:
        horse (int): ID of the horse.
        max_depth (int): How many generations deep to go. e.g. max_depth=2 would return
            back to grandparents at most.

    Returns:
        A nested dict of dicts. The keys are name, id, dam (a dict) and sire (a dict).
    """
    if horse is None:
        return None
    data = table_operations.get_rows('horses', horse).iloc[0]
    output = {}
    output['name'] = data['name']
    output['id'] = data['horse_id']
    output['depth'] = base_depth
    if max_depth > 0:
        output['sire'] = pedigree(data['sire'], max_depth-1, base_depth+1)
        output['dam'] = pedigree(data['dam'], max_depth-1, base_depth+1)
    return output


def kill_horse(horse, date):
    """Kill the specified horse.

    Args:
        horse (int): ID of the horse to kill.
        date (datetime.date): Day of death.
    """
    command = f"SET death_date = '{str(date)}' WHERE horse_id = {horse}"
    table_operations.update_value('horses', command)


def owner_of(horses):
    """Return the owner of the provided horses.

    Args:
        horses (int or list): The id of a horse or a list of horse ids.

    Returns:
        int or list. The id or list of ids of the owners of the horse(s).
    """
    try:
        horses = int(horses)
        output = table_operations.get_column('horses', 'owner_id', [horses])
        return int(output['owner_id'].values[0])
    except TypeError:
        pass
    try:
        horses = list(horses)
        output = table_operations.get_column('horses', 'owner_id', horses)
        return [int(x) for x in output['owner_id'].values]
    except ValueError:
        return None


def coat(horse_id=None, horse_info=None):
    """Return the coat color/pattern of the horse.

    Args:
        horse_id (int): ID of the horse of interest. This will be used to pull the
            horse_info if it is not provided.
        horse_info (pd.Series): The data for the horse.

    Returns:
        String. The name of the horses coat type
    """
    if horse_info is None:
        horse_info = table_operations.get_rows('horses', horse_id).iloc[0]
    return phenotype.base_color(horse_info['dna1'], horse_info['dna2'])


def age(horse_ids, date):
    """Return the ages of some horses.

    args:
        horse_ids (int or list): IDs of the horses of interest.
        date (datetime): Current day.

    returns:
        pd.DataFrame. One column is horse_ids, the other is ages.
    """
    date = pd.to_datetime(date)
    try:
        horse_ids = int(horse_ids)
        query = f"SELECT birth_date, horse_id FROM horses WHERE horse_id = {horse_ids}"
    except ValueError:
        horse_ids = tuple(horse_ids)
        query = f"SELECT birth_date, horse_id FROM horses WHERE horse_id IN {horse_ids}"
    ages = table_operations.query_to_dataframe(query)
    ages['age'] = ages['birth_date'].apply(lambda x: (date - x)/np.timedelta64(1, 'D'))
    return ages[['horse_id', 'age']].copy()


def race_summary(horse_ids):
    """Return a summary of the race performance of the provided horses.

    Args:
        horse_ids (list or int): IDs of horses to get performance values for.

    Return:
          pd.DataFrame. The index is the horse_ids. There are columns for number of 1st,
          2nd, and 3rd place wins as well as total price money.
    """
    o_horse_ids = horse_ids
    try:
        horse_ids = int(horse_ids)
        o_horse_ids = [horse_ids]
        horse_ids = (horse_ids,)
    except TypeError:
        pass
    horse_ids = tuple(horse_ids)
    if len(horse_ids) == 1:
        horse_ids = f'({horse_ids[0]})'
    else:
        horse_ids = str(horse_ids)

    com = "SELECT " \
          "    horse_id, place, winnings " \
          "FROM" \
          "    race_results " \
          "WHERE " \
          f"    horse_id IN {horse_ids}"
    data = table_operations.query_to_dataframe(com)

    output = pd.DataFrame(index=o_horse_ids)
    output['winnings'] = data.groupby('horse_id')['winnings'].sum()

    # Add the number of races run
    number = data.groupby('horse_id').apply(len)
    number.name = 'races run'
    output = pd.merge(output, number, how='outer', right_index=True, left_index=True)
    if 'races run' not in output.columns:
        output['races run'] = 0

    data = data[data['place'] <= 3]
    placing = data.groupby(['horse_id', 'place'])['place'].count().unstack(fill_value=0)

    if 1 not in placing.columns:
        placing[1] = 0
    if 2 not in placing.columns:
        placing[2] = 0
    if 3 not in placing.columns:
        placing[3] = 0
    output = pd.merge(output, placing, how='outer', right_index=True, left_index=True)

    output.fillna(0, inplace=True)
    return output


def expected_race_life():
    """Return the age (in days) and uncertainty at which a horse can expect to run its last race."""
    com = """
    SELECT h.horse_id, r.date, h.birth_date
    FROM race_results rr
        LEFT OUTER JOIN races r ON (rr.race_id = r.race_id)
        LEFT OUTER JOIN horses h ON (rr.horse_id = h.horse_id);
    """
    race_dates = table_operations.query_to_dataframe(com)
    race_dates.drop_duplicates('horse_id', keep='last', inplace=True)
    race_dates['age'] = race_dates['date'] - race_dates['birth_date']
    race_dates['age'] = race_dates['age'].apply(lambda x: x/np.timedelta64(1, 'D'))
    return race_dates['age'].mean(), race_dates['age'].std()


def expected_winnings(horse_id):
    """Return how much money a horse is expected to earn per race.

    This will take into account the horse's past performance and the performance of their
    parents.

    Args:
        horse_id ( int): ID of the horse to determine value for.

    Return:
          float. The amount this horse would be expected to win per race.
    """

    ped = pedigree(horse_id, max_depth=2)
    races = race_summary(all_values(ped, 'id'))
    races['depth'] = all_values(ped, 'depth')
    races['$ per race'] = (races['winnings']/races['races run']).fillna(0)
    races['weight'] = .25**races['depth']*races['races run']
    races['n weight'] = races['weight']/races['weight'].sum()
    return (races['n weight'] * races['$ per race']).sum()


def all_values(dictionary, key):
    """Return all values in a dictionary (and sub dictionaries) associated with the key.

    Args:
        dictionary (dict): Dictionary to get values from.
        key (anything): Dictionary key to get associated values for.

    Return:
        list. All values associated with key in dictionary and subdictionaries.
    """
    output = []
    for k, v in dictionary.items():
        if isinstance(v, dict):
            output += all_values(v, key)
        if k == key:
            output += [v]
    return output


def check_for_injuries(horse_id, event):
    """Roll the dice to see if a horse gets injured during an event.

    Args:
        horse_id (int): ID of the horse to check.
        event (str): Name of the event.

    Return:
        dict. Keys are the
    """
    query = f"SELECT * FROM horse_properties WHERE horse_id = {horse_id}"
    data = table_operations.query_to_dataframe(query).iloc[0]
    output = []
    for injury, info in INJURIES[event].items():
        prob_mult = 1
        for multiplier in info['multipliers']:
            prob_mult *= data[multiplier]
        if random.random() < info['probability']*prob_mult:
            output += [injury]
    return output


def apply_damage(horse_id, part, amount, date=None):
    """Add damage from an injury to a horse.

    Args:
        horse_id (int): ID of the horse.
        part (str): Body part that is injured.
        amount (float): how much damage.
        date (datetime): Only needed if the wound is fatal.
    """
    if amount == 'fatal':
        kill_horse(horse_id, date=date)
    else:
        cmd = f"""
        UPDATE horses SET {part}_damage = {part}_damage + {amount} where horse_id = {horse_id}
        """
        table_operations.cursor.execute(cmd)


def heal_horses(owner_id='all', heal_rate='default'):
    """
    Reduce the damage on all horses' body parts. Typically called each day.
    Args:
        owner_id (int or 'all'): Heal all horses owned by this person. If 'all', will
            heal horses regardless of owner.
        heal_rate (float or 'default'): How much to heal each horse. If 'default' will
            use the heal rate given in the parameter file.
    Returns:
        None.

    """
    if heal_rate == 'default':
        heal_rate = HEAL_RATE

    if owner_id == 'all':
        command = "UPDATE horses SET leg_damage = MAX(0, leg_damage - ?)"
        table_operations.cursor.execute(command, [heal_rate])

        command = "UPDATE horses SET ankle_damage = MAX(0, ankle_damage - ?)"
        table_operations.cursor.execute(command, [heal_rate])

        command = "UPDATE horses SET heart_damage = MAX(0, heart_damage - ?)"
        table_operations.cursor.execute(command, [heal_rate])
    else:
        command = "UPDATE horses SET leg_damage = MAX(0, leg_damage - ?) WHERE owner_id = ?"
        table_operations.cursor.execute(command, [heal_rate, owner_id])

        command = "UPDATE horses SET ankle_damage = MAX(0, ankle_damage - ?) WHERE owner_id = ?"
        table_operations.cursor.execute(command, [heal_rate, owner_id])

        command = "UPDATE horses SET heart_damage = MAX(0, heart_damage - ?) WHERE owner_id = ?"
        table_operations.cursor.execute(command, [heal_rate, owner_id])


def train_horses(owner_id='all', training_amount=0):
    """
    Change the training of horses. Typically called each day.
    Args:
        owner_id (int or 'all'): Train all horses owned by this person. If 'all', will
            train horses regardless of owner.
        training_amount (float): How much to train each horse.
    Returns:
        None.

    """
    if owner_id == 'all':
        command = "UPDATE horses SET training = MIN(MAX(0, training + ?), ?)"
        table_operations.cursor.execute(command, [training_amount, MAX_TRAINING])
    else:
        command = "UPDATE horses SET training = MIN(MAX(0, training + ?), ?) WHERE owner_id = ?"
        table_operations.cursor.execute(command, [training_amount, MAX_TRAINING, owner_id])


def raceable_horses(owner_id=None):
    """Return the ids of all horses owned by the specified owner which are healthy
    enough to race.

    Args:
        owner_id (int, None): Owner to find horses of. If None, will return all
            raceable horses regardless of source.

    Return:
        List. List of all ids of horses.
    """
    if owner_id is None:
        command = """
        SELECT horse_id from horses WHERE
            death_date is NULL 
            and leg_damage + heart_damage + ankle_damage < ?
        """
        params = [HEALTH_CUTOFF]
    else:
        command = """
        SELECT horse_id from horses WHERE
            owner_id = ?
            and death_date is NULL
            and leg_damage + heart_damage + ankle_damage < ?
        """
        params =[owner_id, HEALTH_CUTOFF]
    horses = table_operations.query_to_dataframe(command, params=params)['horse_id'].values
    return [int(x) for x in horses]


class WrongGender(ValueError):
    """Called when the provided horse is the wrong gender."""


class WrongAge(ValueError):
    """Called when the provided horse is the wrong age."""


class PregnancyIssue(Exception):
    """Called when the provided horse is already pregnant."""
