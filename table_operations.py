import os
import numbers
import sqlite3
import numpy as np
import pandas as pd

folder = os.path.dirname(__file__)
db = sqlite3.connect(database=os.path.join(folder, 'game_data.db'))
cursor = db.cursor()

DATE_COLUMNS = ['birth_date', 'death_date', 'expected_death', 'due_date', 'date', 'last_updated']


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


