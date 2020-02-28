import os
import numbers
import sqlite3
import shutil
from inspect import getmembers, isfunction
from io import StringIO
import numpy as np
import pandas as pd
import recalc_phenotype_funcs
import fixed_phenotype_funcs
import game_parameters.constants as c

folder = os.path.join(os.path.dirname(__file__), 'saves')
DATE_COLUMNS = ['birth_date', 'death_date', 'expected_death', 'due_date', 'date', 'last_updated']


def load_save(save_name):
    """Set the active database to be a particular save."""
    global db
    db.close()

    shutil.copyfile(os.path.join(folder, f"{save_name}"),
                    os.path.join(folder, f"active_game.db"))

    db = sqlite3.connect(os.path.join(folder, f"active_game.db"))
    global cursor
    cursor = db.cursor()
    create_empty_tables(overwrite=False)


def save_game(save_name):
    """
    Save the active database to a stored database.
    Args:
        save_name (str): The name of the stored database.

    Returns:
        None.
    """
    shutil.copyfile(os.path.join(folder, f"active_game.db"),
                    os.path.join(folder, f"{save_name}.db"))


def insert_into_table(table, data_dict):
    """Insert a new row into an existing table.

    Args:
        table (str): Name of the table to add the row to.
        data_dict (dict): Column, data pairs to put in the row.

    Return:
        int. The ID of the newly added row.
    """
    if len(data_dict) == 1:
        # When a length-1 tuple is converted into a string, an extra comma is included (e.g.
        # str(tuple([1])) -> '(1,)'. This confuses MySQL and so the comma is removed.
        command = f"INSERT INTO '{table}' {str(tuple(data_dict.keys()))}"
        command = command.replace("'", "`")
        command = command[:-2] + command[-1]
        command += f" VALUES {str(tuple([convert_for_sqlite(v) for v in data_dict.values()]))}"
        command = command[:-2] + command[-1]
    if len(data_dict) > 1:
        command = f"INSERT INTO '{table}' {str(tuple(data_dict.keys()))}"
        command = command.replace("'", "`")
        command += f" VALUES {str(tuple([convert_for_sqlite(v) for v in data_dict.values()]))}"
    cursor.execute(command)
    db.commit()
    return cursor.lastrowid


def update_table(table, data_dict, primary_key_val):
    """Update a table with the provided data.
    Args:
        table (str): Name of the table to add the row to.
        data_dict (dict): Column, data pairs to put in the row.
        primary_key_val (int): Primary key to add this data to.

    Return:
        Nothing.
    """
    pk_name = primary_key(table)

    com = f"""
    UPDATE {table}
    SET
    """
    for k, v in data_dict.items():
        com += f"{k} = {v},"
    com = com[:-1]
    com += f" WHERE {pk_name} = {primary_key_val}"
    cursor.execute(com)


def insert_dataframe_into_table(table, data):
    """Insert the data contained in a pandas DataFrame into an existing table. All columns
    in the dataframe will be added and should already be in the table.

    Args:
        table (str): Name of the table to add the rows to.
        data (pd.DataFrame): Data to add.
    """
    data.to_sql(table, db, if_exists='append', index=False)


def format_list(seq):
    """Format a sequence of values for a sql query.

    e.g. ['boy', 'man', 'lady'] -> '(boy, man, lady)'
    """
    output = '('
    for i in range(len(seq) - 1):
        output += f'{seq[i]}, '
    output += seq[-1]
    output += ')'
    return output


def qmark_list(number):
    """Return a string like '(?, ?, ?, ?)' ."""
    if number == 0:
        return '()'
    output = '('
    for i in range(number-1):
        output += '?, '
    output += '?)'
    return output


def whole_table(table):
    """Convert a table in the database into a pandas dataframe."""
    command = f"SELECT * from {table}"
    return query_to_dataframe(command)


def primary_key(table):
    """Return the first primary key of the given table."""
    table_info = pd.read_sql_query(f'PRAGMA table_info({table})', db)
    return table_info.loc[table_info['pk'] == 1, 'name'].values[0]


def get_rows(table, ids):
    """Get rows from table with primary key in ids.

    Args:
        table (str): Name of table to get data for.
        ids (list, str, or int): Values of the primary key to match.

    Return:
        pd.DataFrame containing the data. Index are the ids.
    """
    if not isinstance(ids, list):
        ids = f"({ids})"
    elif len(ids) == 1:
        ids = f"({ids[0]})"
    else:
        ids = tuple(ids)

    pk = primary_key(table)

    command = f"SELECT * from {table} where {pk} IN {ids}"
    return query_to_dataframe(command)


def get_column(table, column, ids='all'):
    """Get a specific column from a table with primary key in ids.

    Args:
        table (str): Name of table to get data for.
        ids (list, str, or int, 'all'): Values of the primary key to match. If 'all', will
            return the entire column.
        column (str): Name of the column to get data for.

    Return:
        pd.DataFrame containing the column data. Index are the ids.
    """
    pk = primary_key(table)
    if ids != 'all':
        if not isinstance(ids, list):
            ids = f"({ids})"
        elif len(ids) == 1:
            ids = f"({ids[0]})"
        else:
            ids = tuple(ids)
        command = f"SELECT {pk}, {column} from {table} where {pk} IN {ids}"
    else:
        command = f"SELECT {pk}, {column} from {table}"
    return query_to_dataframe(command)


def get_primary_index(table):
    """Return the primary index values of a table."""
    pk = primary_key(table)
    command = f"SELECT {pk} from {table}"
    return list(pd.read_sql_query(command, db)[pk].values)


def update_value(table, command):
    """Update values in a table using the specified command."""
    command = f"UPDATE {table} " + command
    cursor.execute(command)
    db.commit()


def query_to_dataframe(query, params=[]):
    """Return the query as a pandas dataframe."""
    return pd.read_sql_query(query, db, params=params, parse_dates=DATE_COLUMNS)


def list_tables():
    """Return a list of tables in the database."""
    names = cursor.execute("SELECT name FROM sqlite_master;")
    return [x[0] for x in names]


def delete_tables(tables):
    if isinstance(tables, str):
        tables = [tables]
    for table in tables:
        cursor.execute(f"DROP TABLE IF EXISTS {table}")


def clear_tables(tables):
    """Remove all data in tables.

    Args:
        tables (str or list): Table(s) to clear.
    """
    if isinstance(tables, str):
        tables = [tables]
    for table in tables:
        cursor.execute(f"DELETE FROM {table}")


def convert_for_sqlite(value):
    """Convert a value into a form that sqlite can handle."""
    if isinstance(value, str):
        return value
    if isinstance(value, numbers.Number):
        return value
    try:
        value = pd.to_datetime(value)
        return str(value)
    except ValueError:
        raise ValueError(f"{value} cannot be converted into a form for storage in a database.")


def create_empty_tables(overwrite=True):
    """
    Create empty tables in the loaded database.
    Args:
        overwrite (bool): If True, will delete any existing tables in the database and so
            create all blank tables. If False, will only create blank tables for any that
            are missing.

    Returns:
        None.

    """
    # Create all the necessary tables
    tables = {}
    base_pairs = c.CHROMOSOME_LENGTH * c.GENE_LENGTH
    tables['horses'] = """
    CREATE TABLE IF NOT EXISTS horses (
        horse_id INTEGER PRIMARY KEY,
        birth_date TEXT NOT NULL,
        death_date TEXT DEFAULT NULL,
        expected_death TEXT NOT NULL,
        name TEXT NOT NULL,
        gender TEXT check(gender in ('M', 'F')),
        owner_id INTEGER,
        due_date TEXT DEFAULT NULL,
        impregnated_by INTEGER DEFAULT NULL,
        dam INTEGER DEFAULT NULL,
        sire INTEGER DEFAULT NULL,
        dna1 TEXT,
        dna2 TEXT,
        leg_damage REAL DEFAULT 0,
        ankle_damage REAL DEFAULT 0,
        heart_damage REAL DEFAULT 0,
        training REAL DEFAULT 0,
        FOREIGN KEY (owner_id) REFERENCES owners (owner_id)
        )"""

    tables['owners'] = """
    CREATE TABLE IF NOT EXISTS owners (
        owner_id INTEGER PRIMARY KEY,
        money INTEGER NOT NULL,
        name TEXT NOT NULL
        )"""

    tables['races'] = """
    CREATE TABLE IF NOT EXISTS races (
        race_id INTEGER PRIMARY KEY,
        date TEXT NOT NULL,
        total_purse INTEGER DEFAULT 0,
        distance REAL NOT NULL
        )"""

    tables['race_results'] = """
    CREATE TABLE IF NOT EXISTS race_results (
        result_id INTEGER PRIMARY KEY,
        horse_id INTEGER NOT NULL,
        race_id INTEGER NOT NULL,
        time REAL,
        place INTEGER,
        winnings INTEGER DEFAULT 0,
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
    tables['horse_properties'] = prop_table

    employee_table = """
    CREATE TABLE IF NOT EXISTS employees (
        employee_id INTEGER PRIMARY KEY,
        employer INTEGER DEFAULT 1,
        salary REAL DEFAULT 0,
        employee_type TEXT NOT NULL,
        name TEXT NOT NULL,
    """
    cols = []
    for employee in c.EMPLOYEES.keys():
        cols += list(c.EMPLOYEES[employee]['bonuses'].keys())
    for col in set(cols):
        employee_table += f"{col} float DEFAULT 0,\n"
    employee_table += "FOREIGN KEY (employer) REFERENCES owners (owner_id))"
    tables['employees'] = employee_table

    estate_table = """
    CREATE TABLE IF NOT EXISTS estates (
        owner_id INTEGER PRIMARY KEY,
        total_land REAL DEFAULT 0,
        free_land REAL DEFAULT 0,
    """
    for b in list(c.BUILDINGS.keys())[:-1]:
        estate_table += f"{b} integer DEFAULT 0,\n"
    estate_table += f"{list(c.BUILDINGS.keys())[-1]} INTEGER DEFAULT 0);"
    tables['estates'] = estate_table

    tables['game_info'] = """
    CREATE TABLE IF NOT EXISTS game_info (
        date TEXT DEFAULT '2000-01-01',
        date_increment INTEGER DEFAULT 0)"""

    tables['calendar'] = """
    CREATE TABLE IF NOT EXISTS calendar (
        date TEXT NOT NULL,
        name TEXT NOT NULL,
        type TEXT,
        PRIMARY KEY (date, name))
    """

    if overwrite:
        delete_tables(tables.keys())

    for name, table in tables.items():
        print(f"Creating table {name}. ")
        cursor.execute(table)
    db.commit()


def game_info_state():
    """
    Return the content of the game_info table in the form of a dictionary. Return None,
    if there is no saved info.
    """
    data = pd.read_sql_query("SELECT * FROM game_info LIMIT 1", db)
    if len(data) == 0:
        return None
    return data.iloc[0].to_dict()


db = sqlite3.connect(os.path.join(folder, "active_game.db"))
cursor = db.cursor()
create_empty_tables(overwrite=False)
