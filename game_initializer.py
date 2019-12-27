import os
import sqlite3
#import mysql.connector as mysql
#from mysql.connector import errorcode
import table_operations
try:
    from game_parameters.local_constants import *
except ModuleNotFoundError:
    from game_parameters.constants import *
import game_parameters.parameter_checker

folder = os.path.dirname(__file__)
db = sqlite3.connect(os.path.join(folder, 'game_data.db'))
cursor = db.cursor()

table_operations.delete_tables(['horses', 'owners', 'races', 'race_results'])


# Create all the necessary tables
tables = {}
base_pairs = CHROMOSOME_LENGTH * GENE_LENGTH
tables['horses'] = """
CREATE TABLE IF NOT EXISTS horses (
    id integer PRIMARY KEY,
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
    FOREIGN KEY (owner_id) REFERENCES owners (owner_id)
    )"""
tables['owners'] = """
CREATE TABLE IF NOT EXISTS owners (
    id integer PRIMARY KEY,
    money integer NOT NULL,
    name text NOT NULL
    )"""

tables['races'] = """
CREATE TABLE IF NOT EXISTS races (
    id integer PRIMARY KEY,
    date text NOT NULL,
    total_purse integer DEFAULT 0,
    distance float NOT NULL
    )"""

tables['race_results'] = """
CREATE TABLE IF NOT EXISTS race_results (
    id integer PRIMARY KEY,
    horse_id integer NOT NULL,
    race_id integer NOT NULL,
    time float NOT NULL,
    place integer,
    winnings integer DEFAULT 0,
    FOREIGN KEY (horse_id) REFERENCES horses (id)
    FOREIGN KEY (race_id) REFERENCES races (id)
    )"""

for name, table in tables.items():
    print(f"Creating table {name}. ")
    cursor.execute(table)
