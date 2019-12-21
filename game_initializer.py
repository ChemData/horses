import os
import mysql.connector as mysql
from mysql.connector import errorcode
import table_operations
from game_parameters.constants import *
import game_parameters.parameter_checker


# Check that a username and password are stored in the environment variables
try:
    os.environ['sql_username']
except KeyError:
    os.environ['sql_username'] = input('What is your sql username?')

try:
    os.environ['sql_pw']
except KeyError:
    os.environ['sql_pw'] = input('What is your sql password?')


db = mysql.connect(user=os.environ['sql_username'],
                   password=os.environ['sql_pw'],
                   host='localhost')
cursor = db.cursor()


# Create the database if it is missing
try:
    cursor.execute('CREATE DATABASE horse_game')
except mysql.errors.DatabaseError:
    print('The necessary database already exists')
cursor.execute('USE horse_game')


# Create all the necessary tables
tables = {}
base_pairs = CHROMOSOME_LENGTH * GENE_LENGTH
tables['horses'] = (
    "CREATE TABLE `horses` ("
    "  `horse_id` int(11) NOT NULL AUTO_INCREMENT,"
    "  `birth_date` date NOT NULL,"
    "  `death_date` date DEFAULT NULL,"
    "  `expected_death` date NOT NULL,"
    f"  `name` varchar({HORSE_NAME_MAX}) NOT NULL,"
    "  `gender` enum('M','F') NOT NULL,"
    "  `owner_id` int(12) NOT NULL,"
    "  `due_date` date DEFAULT NULL,"
    "  `impregnated_by` int(11) DEFAULT NULL,"
    "  `dam` int(11),"
    "  `sire` int(11),"
    f"  `dna1` varchar({base_pairs}),"
    f"  `dna2` varchar({base_pairs}),"
    "  PRIMARY KEY (`horse_id`)"
    ") ENGINE=InnoDB")

tables['owners'] = (
    "CREATE TABLE `owners` ("
    "  `owner_id` int(8) NOT NULL AUTO_INCREMENT,"
    "  `money` decimal(10, 2) NOT NULL,"
    f"  `name` varchar({OWNER_NAME_MAX}) NOT NULL,"
    "  PRIMARY KEY (`owner_id`)"
    ") ENGINE=InnoDB")

tables['races'] = (
    "CREATE TABLE  `races` ("
    "  `race_id` int(8) NOT NULL AUTO_INCREMENT,"
    "  `time` DATETIME NOT NULL,"
    "  `total_purse` decimal(10,2),"
    "  `distance` float,"
    "  PRIMARY KEY (`race_id`)"
    ") ENGINE=InnoDB")

tables['race_results'] = (
    "CREATE TABLE  `race_results` ("
    "  `result_id` int(8) NOT NULL AUTO_INCREMENT,"
    "  `horse_id` int(11) NOT NULL,"
    "  `race_id` int(8) NOT NULL,"
    "  `time` float,"
    "  `place` int,"
    "  `winnings` decimal(10,2),"
    "  PRIMARY KEY (`result_id`)"
    ") ENGINE=InnoDB")

for table in tables:
    table_description = tables[table]
    try:
        print("Creating table {}: ".format(table), end='')
        cursor.execute(table_description)
    except mysql.Error as err:
        if err.errno == errorcode.ER_TABLE_EXISTS_ERROR:
            print("already exists.")
        else:
            print(err.msg)
    else:
        print("OK")

table_operations.clear_tables(tables.keys())

