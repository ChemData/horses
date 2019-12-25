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
