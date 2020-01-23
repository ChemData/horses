import os
import json

# Genetics
GENE_LENGTH = 6  # Basepairs per gene
CHROMOSOME_LENGTH = 20  # Genes per chromosome
DEFAULT_WELL_FORMED_CUTOFF = 0.1  # Default value for difficulty of a gene being well formed.
                                # Higher is harder.


# Other param files
PARAMS_FOLDER = os.path.dirname(__file__)
try:
    with open(os.path.join(PARAMS_FOLDER, 'local_genes.json'), 'r') as f:
        GENES = json.load(f)
except FileNotFoundError:
    with open(os.path.join(PARAMS_FOLDER, 'genes.json'), 'r') as f:
        GENES = json.load(f)

try:
    with open(os.path.join(PARAMS_FOLDER, 'local_buildings.json'), 'r') as f:
        BUILDINGS = json.load(f)
except FileNotFoundError:
    with open(os.path.join(PARAMS_FOLDER, 'buildings.json'), 'r') as f:
        BUILDINGS = json.load(f)

try:
    with open(os.path.join(PARAMS_FOLDER, 'local_injuries.json'), 'r') as f:
        INJURIES = json.load(f)
except FileNotFoundError:
    with open(os.path.join(PARAMS_FOLDER, 'injuries.json'), 'r') as f:
        INJURIES = json.load(f)
try:
    with open(os.path.join(PARAMS_FOLDER, 'local_employees.json'), 'r') as f:
        EMPLOYEES = json.load(f)
except FileNotFoundError:
    with open(os.path.join(PARAMS_FOLDER, 'employees.json'), 'r') as f:
        EMPLOYEES = json.load(f)


# Naming
HORSE_NAME_MAX = 24  # Longest permitted name for a horse
OWNER_NAME_MAX = 24  # Longest permitted name for an owner

# Event Probabilities
RACE_PROBABILITY = 0  # Probability that a race will occur each day

# Horse life times
SEXUAL_MATURITY = 730  # Age (in days) when breeding can occur
GESTATION_MEAN = 340  # Mean time (in days) that gestation takes
GESTATION_STD = 15  # Standard deviation of gestation time
LIFE_MEAN = 9490  # Mean lifespan (in days)
LIFE_STD = 730  # Lifespan standard deviation
PROPERTY_UPDATE = 30  # How frequently to update a horse's anatomical information

# Economic Values
MEAT_PRICE = 200  # How much a horse can be sold to the abattoir for

# Training Info
TRAINING_DECAY = 1  # Amount that a horse's training will decrease by each day
MAX_TRAINING = 100  # Maximum amount of training that a horse can have
AI_TRAINING = 1.5  # How much training the horses of the AI players receive each day

# Injury Info
HEAL_RATE = 1  # Number of points of damage body parts will heal each day
HEALTH_CUTOFF = 25  # A horse cannot race if total damage is greater than this value

# Estates
STARTING_MONEY = 10000  # How much money each player starts with
INIT_ESTATE_SIZE = 100  # Starting size of estates in hectares
PASTURE_AMT = 5  # Hectares of pasture needed per horse
LAND_COST = 1000  # Cost to buy one hectare of open land

# Employees
MEAN_POINTS = 4  # Average number of points per bonus type to assign to a new employee
STD_POINTS = 1  # The standard deviation of points
BASE_SALARY = 50  # What every employee makes per week
SALARY_MULTIPLIER = 25  # How much more an employee is paid per skill point

try:
    from game_parameters.local_constants import *
except ModuleNotFoundError:
    pass
