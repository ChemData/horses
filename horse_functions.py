import os
import datetime
import json
import numpy as np
import pandas as pd
import table_operations
import genetics
import phenotype
try:
    from game_parameters.local_constants import *
except ModuleNotFoundError:
    from game_parameters.constants import *

try:
    with(open(os.path.join(PARAMS_FOLDER, 'local_horse_names.json'), 'r')) as f:
        HORSE_NAMES = json.load(f)
except FileNotFoundError:
    with(open(os.path.join(PARAMS_FOLDER, 'horse_names.json'), 'r')) as f:
        HORSE_NAMES = json.load(f)


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
    return new_id


def trade_horse(horse_id, new_owner_id):
    """Transfer owndership of a horse from one owner to another."""
    command = f"SET owner_id = {new_owner_id} WHERE id = {horse_id}"
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
    data.set_index('id', inplace=True)

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
    command = f"SET due_date = '{str(due_date)}' WHERE id = {lady_horse.name}"
    table_operations.update_value('horses', command)

    command = f"SET impregnated_by = '{man_horse.name}' WHERE id = {lady_horse.name}"
    table_operations.update_value('horses', command)


def give_birth(horse, date, name=None):
    """Make a horse give birth to a pony."""
    dam = table_operations.get_rows('horses', horse).iloc[0]

    if dam['impregnated_by'] is None:
        raise PregnancyIssue(f'{horse} is not pregnant and so cannot give birth.')

    sire = table_operations.get_rows('horses', dam['impregnated_by']).iloc[0]

    foal = make_random_horse(date)
    foal['dam'] = dam['id']
    foal['sire'] = sire['id']
    foal['owner_id'] = dam['owner_id']
    foal['birth_date'] = str(date)
    foal['expected_death'] = str(date + datetime.timedelta(
        round(np.random.normal(LIFE_MEAN, LIFE_STD))))
    if name is not None:
        foal['name'] = name
    mix_genomes(dam, sire, foal)
    new_id = add_horse(foal)

    command = f"SET impregnated_by = NULL WHERE id = {horse}"
    table_operations.update_value('horses', command)

    command = f"SET due_date = NULL WHERE id = {horse}"
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


def pedigree(horse, max_depth=3):
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
    output['id'] = data.name
    output['sire'] = pedigree(data['sire'], max_depth-1)
    output['dam'] = pedigree(data['dam'], max_depth-1)
    return output


def kill_horse(horse, date):
    """Kill the specified horse.

    Args:
        horse (int): ID of the horse to kill.
        date (datetime.date): Day of death.
    """
    command = f"SET death_date = '{str(date)}' WHERE id = {horse}"
    table_operations.update_value('horses', command)


def owner_of(horses):
    """Return the owner of the provided horses.

    Args:
        horses (int or list): The id of a horse or a list of horse ids.

    Returns:
        int or list. The id or list of ids of the owners of the horse(s).
    """
    if isinstance(horses, int):
        output = table_operations.get_column('horses', 'owner_id', [horses])
        return output['owner_id'].values[0]
    try:
        horses = list(horses)
        output = table_operations.get_column('horses', 'owner_id', horses)
        return list(output['owner_id'].values)
    except ValueError:
        return None


def speed(horse_id=None, horse_info=None):
    """Return the speed of the horse.

    Args:
        horse_id (int): ID of the horse of interest. This will be used to pull the
            horse_info if it is not provided.
        horse_info (pd.Series): The data for the horse.

    Returns:
        Float. The speed in m/s of the horse.
    """
    if horse_info is None:
        horse_info = table_operations.get_rows('horses', horse_id).iloc[0]
    return phenotype.speed(horse_info['dna1'], horse_info['dna2'])


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


class WrongGender(Exception):
    """Called when the provided horse is the wrong gender."""


class WrongAge(Exception):
    """Called when the provided horse is the wrong age."""


class PregnancyIssue(Exception):
    """Called when the provided horse is already pregnant."""
