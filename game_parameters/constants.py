import os
import json

# Genetics
GENE_LENGTH = 6  # Basepairs per gene
CHROMOSOME_LENGTH = 20  # Genes per chromosome
DEFAULT_WELL_FORMED_CUTOFF = 0  # Default value for difficulty of a gene being well formed.
                                # Higher is harder.
folder = os.path.dirname(__file__)
with open(os.path.join(folder, 'genes.json'), 'r') as f:
    GENES = json.load(f)


# Naming
HORSE_NAME_MAX = 24  # Longest permitted name for a horse
OWNER_NAME_MAX = 24  # Longest permitted name for an owner

# Event Probabilities
RACE_PROBABILITY = 0  # Probability that a race will occur each day

# Horse development times
SEXUAL_MATURITY = 730  # Age (in days) when breeding can occur
GESTATION_MEAN = 340  # Mean time (in days) that gestation takes
GESTATION_STD = 15  # Standard deviation of gestation time
LIFE_MEAN = 9490  # Mean lifespan (in days)
LIFE_STD = 730  # Lifespan standard deviation
