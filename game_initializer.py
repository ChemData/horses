import os
import sqlite3
from inspect import getmembers, isfunction
import table_operations
import recalc_phenotype_funcs
import fixed_phenotype_funcs

from game_parameters.constants import *
import game_parameters.parameter_checker


def create_empty_tables():
    folder = os.path.dirname(__file__)
    db = sqlite3.connect(os.path.join(folder, 'game_data.db'))
    cursor = db.cursor()

    table_operations.delete_tables(['horses', 'owners', 'races', 'race_results',
                                    'horse_properties', 'employees'])


    # Create all the necessary tables
    tables = {}
    base_pairs = CHROMOSOME_LENGTH * GENE_LENGTH
    tables['horses'] = """
    CREATE TABLE IF NOT EXISTS horses (
        horse_id integer PRIMARY KEY,
        birth_date text NOT NULL,
        death_date text DEFAULT NULL,
        expected_death text NOT NULL,
        name text NOT NULL,
        gender text check(gender in ('M', 'F')),
        owner_id integer,
        due_date text DEFAULT NULL,
        impregnated_by integer DEFAULT NULL,
        dam integer DEFAULT NULL,
        sire integer DEFAULT NULL,
        dna1 text,
        dna2 text,
        leg_damage float DEFAULT 0,
        ankle_damage float DEFAULT 0,
        heart_damage float DEFAULT 0,
        training float DEFAULT 0,
        FOREIGN KEY (owner_id) REFERENCES owners (owner_id)
        )"""

    tables['owners'] = """
    CREATE TABLE IF NOT EXISTS owners (
        owner_id integer PRIMARY KEY,
        money integer NOT NULL,
        name text NOT NULL
        )"""

    tables['races'] = """
    CREATE TABLE IF NOT EXISTS races (
        race_id integer PRIMARY KEY,
        date text NOT NULL,
        total_purse integer DEFAULT 0,
        distance float NOT NULL
        )"""

    tables['race_results'] = """
    CREATE TABLE IF NOT EXISTS race_results (
        result_id integer PRIMARY KEY,
        horse_id integer NOT NULL,
        race_id integer NOT NULL,
        time float,
        place integer,
        winnings integer DEFAULT 0,
        FOREIGN KEY (horse_id) REFERENCES horses (horse_id)
        FOREIGN KEY (race_id) REFERENCES races (race_id)
        )"""

    prop_table = """
    CREATE TABLE IF NOT EXISTS horse_properties (
        horse_id integer PRIMARY KEY,
    """
    for func_name in [x[0] for x in getmembers(recalc_phenotype_funcs) if isfunction(x[1])]:
        prop_table += f'{func_name} float,'

    for func_name in [x[0] for x in getmembers(fixed_phenotype_funcs) if isfunction(x[1])]:
        prop_table += f'{func_name} float,'
    prop_table += "FOREIGN KEY (horse_id) REFERENCES horses (horse_id))"
    tables['prop_table'] = prop_table

    employee_table = """
    CREATE TABLE IF NOT EXISTS employees (
        employee_id integer PRIMARY KEY,
        employer integer DEFAULT 1,
        salary float DEFAULT 0,
        employee_type string NOT NULL,
        name string NOT NULL,
    """
    cols = []
    for employee in EMPLOYEES.keys():
        cols += list(EMPLOYEES[employee]['bonuses'].keys())
    for c in set(cols):
        employee_table += f"{c} float DEFAULT 0,\n"
    employee_table += "FOREIGN KEY (employer) REFERENCES owners (owner_id))"

    tables['employee_table'] = employee_table


    for name, table in tables.items():
        print(f"Creating table {name}. ")
        cursor.execute(table)
