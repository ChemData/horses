from inspect import getmembers, isfunction
import numpy as np
import pandas as pd
import recalc_phenotype_funcs as recalc
import fixed_phenotype_funcs as fixed
import table_operations as to
from game_parameters.constants import *

"""
Phenotypic system

The goal here is to convert a horse's DNA (genotype) into useful, player-relevant properties
(phenotype). For instance, we want to know how fast a horse will run based on the activity of its
genes.json controlling weight, muscle size, etc.

This model consists of three layers.
1) Genotype. Each horse has two chromosomes consisting of many genes.json. A given allele for a gene
    has an activity level ranging from 0 (inactive) to 1 (very active). Genotype is hard for the
    the player to see/measure.
2) Anatomy. These properties are directly derived from genotype. For instance, heart size, weight,
    muscle twitch speed. Multiple genes.json can determine a single anatomic property and one gene can
    feed into multiple anatomic properties. So, a gene controlling growth hormone production might
    lead to a larger heart size and a higher weight. For ease of later computation, anatomic
    properties are scaled from 0 to 1, often by a sigmoid function. The player has partial access
    to anatomy and may need special equipment to get more information. So, heart size is initially
    found only by autopsy but could be determined in vivo if the player purchased an MRI machine.
    In the future, it would be smart to mix in environmental factors here: random chance, training,
    food quality, etc. [A thought: make it so no anatomic features are directly accesible. Instead,
    if you want the player to be able to access the property, there must be a stat
    which is derived purely from the anatomy. Thus, anatomy properties can always range from 0 to 1
    and stats can always have reasonable real-world scaling. For instance, the heart_size property
    would determine the heart_size stat, the latter of which would range from  3.5 to 4.5 kg.]
3) Stats. These properties are directly derived from anatomy. Stats include speed, acceleration,
    injury probability, etc. They may be derived from one or more anatomic property and one
    anatomic property can influence multiple stats. Stats may initially be scaled from 0 to 1 but
    should be converted into real world values (e.g. speed should be scaled to about 12-17 m/s).
    These will tend to be player measureable properties like height, leg length, etc. Some will,
    however, not be measurable like heart failure probability.
    
A different but related model is used for things like coat color.
1) Genotype. Each horse has two chromosomes consisting of many genes.json. A given allele for a gene
    has an activity level ranging from 0 (inactive) to 1 (very active). If a gene is not inactive,
    the specific genotype form is calculated by dividing the activity range into pieces. For
    instance, If the Agouti gene is inactive it will have genotype form "a". If it is active, its
    activity will range between (0, 1). (0, .25) might yield "At". [0.25, 0.75) might yield "A".
    And [0.75, 1) might yield "A+". The exact ranges would be set separately for each gene.
2) Anatomy. If-then logic takes the genotype to actual attributes. The primary example is coat
    color/pattern. By looking at all the genes.json, we determine what the horse's color/pattern name is
    "Black", 'White", "Cremello", etc.
"""


to_recalc = [x for x in getmembers(recalc) if isfunction(x[1])]

to_fix = [x for x in getmembers(fixed) if isfunction(x[1])]


def calc_properties(horse_id):
    """(Re)calculate the properties of a horse and store these results."""
    query = f"""
    SELECT horse_id
    FROM horse_properties\
    WHERE horse_id = {horse_id}"""
    data = to.query_to_dataframe(query)

    dna1, dna2 = get_dna(horse_id)
    new_data = {}
    for k, v in to_recalc:
        new_data[k] = v(dna1, dna2)

    if len(data) == 0:
        new_data['horse_id'] = horse_id
        for k, v in to_fix:
            new_data[k] = v(dna1, dna2)
        to.insert_into_table('horse_properties', new_data)
    else:
        to.update_table('horse_properties', new_data, horse_id)


def update_properties(dead_too=False):
    """Recalculate the properties of all horses and update the table.

    Args:
        dead_too (bool): If False, will only recalculate the values for living horses.

    Returns:
        None
    """
    if dead_too:
        query = "SELECT horse_id FROM horses"
    else:
        query = "SELECT horse_id FROM horses WHERE death_date is Null"
    horses = to.query_to_dataframe(query)
    for h in horses['horse_id']:
        calc_properties(h)


def h_prop(property, horse_id, day=None):
    """Return the property for the horse. If (re)calculation is needed, the results will
    be saved.

    Args:
        property (str): Name of the property to return
        horse_id (id): ID of the horse in question
        day (datetime or None): Day in the horse simulation, if the existing data is too
            old, it will recalculate. If None, it will not worry about the age of the
            data. If None, and there is no data, will calculate the data but will not save
            it.

    Returns: The property of the horse.

    """
    query = f"""
    SELECT {property}, last_updated
    FROM horse_properties\
    WHERE horse_id = {horse_id}"""
    try:
        data = to.query_to_dataframe(query).iloc[0]
    except IndexError:
        data = None

    # If there is no need to update, and we have the data
    if data is not None:
        if day is None:
            day = data['last_updated']
        day_diff = (pd.to_datetime(day) - data['last_updated']).days
        if day_diff < PROPERTY_UPDATE:
            return data[property]

    dna1, dna2 = get_dna(horse_id)
    # If we just need to calculate one value and return it
    if day is None:
        try:
            return getattr(recalc, property)(dna1, dna2)
        except:
            return getattr(fixed, property)(dna1, dna2)

    # If we need to update or add data
    new_data = {'last_updated': day}
    for k, v in to_recalc:
        new_data[k] = v(dna1, dna2)

    if data is None:
        new_data['horse_id'] = horse_id
        for k, v in to_fix:
            new_data[k] = v(dna1, dna2)
        to.insert_into_table('horse_properties', new_data)
    else:
        to.update_table('horse_properties', new_data, horse_id)

    try:
        return new_data[property]
    except KeyError:
        return data[property]


def get_dna(horse_id):
    """Return the DNA of a horse.

    Args:
        horse_id (int): ID of the horse.

    Returns:
        str. First chromosome.
        str. Second chromosome.
    """
    query = f"""
    SELECT dna1, dna2
        FROM horses
        WHERE horse_id = {horse_id}
    """
    data = to.query_to_dataframe(query)[['dna1', 'dna2']].values
    return data[0][0], data[0][1]


def sigmoid(x):
    return 1/(1+np.exp(-x))
