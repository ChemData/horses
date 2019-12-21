import os
import numbers
import numpy as np
import pandas as pd
import mysql.connector as mysql
from mysql.connector import errorcode


db = mysql.connect(user=os.environ['sql_username'],
                   password=os.environ['sql_pw'],
                   host='localhost',
                   database='horse_game')
cursor = db.cursor()


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
        command += f" VALUES {str(tuple([convert_for_mysql(v) for v in data_dict.values()]))}"
        command = command[:-2] + command[-1]
    if len(data_dict) > 1:
        command = f"INSERT INTO '{table}' {str(tuple(data_dict.keys()))}"
        command = command.replace("'", "`")
        command += f" VALUES {str(tuple([convert_for_mysql(v) for v in data_dict.values()]))}"
    cursor.execute(command)
    db.commit()
    return cursor.lastrowid


def insert_dataframe_into_table(table, data):
    """Insert the data contained in a pandas DataFrame into an existing table. All columns
    in the dataframe will be added and should already be in the table.

    Args:
        table (str): Name of the table to add the rows to.
        data (pd.DataFrame): Data to add.
    """
    command = f"INSERT INTO '{table}' {str(tuple(data.columns))}"
    command += " VALUES"
    for i, row in data.iterrows():
        if i != 0:
            command += ','
        command += str(tuple(row.values))
    command = command.replace("'", "`")
    cursor.execute(command)
    db.commit()


def whole_table(table):
    """Convert a table in the database into a pandas dataframe."""
    command = f"SELECT * from {table}"
    return table_to_df(command)


def table_to_df(command, set_index_from_first_column=True):
    """Call a selection command on a table and convert the result into a DataFrame."""
    cursor.execute(command)
    col_names = [x[0] for x in cursor.description]
    output = pd.DataFrame(columns=col_names)
    c = 0
    for row in cursor:
        output.loc[c] = row
        c += 1
    if set_index_from_first_column:
        output.set_index(col_names[0], inplace=True)
    return output


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

    cursor.execute(f"SHOW INDEXES FROM {table}")
    primary_key = cursor.__next__()[4]

    command = f"SELECT * from {table} where {primary_key} IN {ids}"
    return table_to_df(command)


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
    cursor.execute(f"SHOW INDEXES FROM {table}")
    primary_key = cursor.__next__()[4]
    if ids != 'all':
        if not isinstance(ids, list):
            ids = f"({ids})"
        elif len(ids) == 1:
            ids = f"({ids[0]})"
        else:
            ids = tuple(ids)
        command = f"SELECT {primary_key}, {column} from {table} where {primary_key} IN {ids}"
    else:
        command = f"SELECT {primary_key}, {column} from {table}"
    return table_to_df(command)


def get_primary_index(table):
    """Return the primary index values of a table."""
    cursor.execute(f"SHOW INDEXES FROM {table}")
    primary_key = cursor.__next__()[4]
    command = f"SELECT {primary_key} from {table}"
    return list(table_to_df(command, set_index_from_first_column=False)[primary_key].values)


def update_value(table, command):
    """Update values in a table using the specified command."""
    command = f"UPDATE {table} " + command
    cursor.execute(command)
    db.commit()


def list_tables():
    """Return a list of tables in the database."""
    cursor.execute('show tables')
    output = []
    for i in cursor:
        output += [i[0]]
    return output


def delete_tables(tables):
    if isinstance(tables, str):
        tables = [tables]
    for table in tables:
        try:
            cursor.execute(f"DROP TABLE {table}")
        except mysql.errors.ProgrammingError:
            pass


def clear_tables(tables):
    """Remove all data in tables.

    Args:
        tables (str or list): Table(s) to clear.
    """
    if isinstance(tables, str):
        tables = [tables]
    for table in tables:
        try:
            cursor.execute(f"TRUNCATE TABLE {table}")
        except mysql.errors.ProgrammingError:
            pass


def convert_for_mysql(value):
    """Convert a value into a form that my sql can handle."""
    if isinstance(value, str):
        return value
    if isinstance(value, numbers.Number):
        return value
    try:
        value = pd.to_datetime(value)
        return str(value)
    except ValueError:
        raise ValueError(f"{value} cannot be converted into a form for storage in a database.")


