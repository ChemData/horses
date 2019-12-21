import os
import game_parameters.constants as c

"""
The goal is to check parameters for correctness. Certain values must be within particular
ranges.
"""


def check_genes():
    for name, gene in c.GENES.items():
        # Check that gene has a reasonable position number
        try:
            pos = gene['pos']
        except ValueError:
            raise ValueError(f"The gene {name} lacks a chromosomal position (pos).")
        if pos >= c.CHROMOSOME_LENGTH:
            raise ValueError(f"The gene {name}'s position ({pos}) is beyond the length of the"
                             f" chromosome ({c.CHROMOSOME_LENGTH}")

        # A gene doesn't need to have a specific cutoff (it can use the default), but it it does
        # it must be between 0 and  1.
        cutoff = gene.get('cutoff', 0)
        if cutoff < 0 or cutoff > 1:
            raise ValueError(f"The gene {name} has a cutoff of {cutoff}. It must be between 0 and 1"
                             f" inclusive.")

        # If a gene has specified alleles, it must have a few other things
        try:
            alleles = gene['alleles']
            ranges = gene.get('ranges', [])

            # There must be one fewer range than allele. If there is only one allele,
            # ranges can be omitted
            if len(alleles) - 1 != len(ranges):
                raise ValueError(f"The gene {name} has {len(alleles)} listed alleles but"
                                 f" only {len(ranges)} ranges, it must have one fewer"
                                 f" range than allele.")

            # There must be a broken allele
            try:
                gene['broken']
            except KeyError:
                raise ValueError(f"The gene {name} needs a name for the broken allele.")
        except KeyError:
            pass


check_genes()
print('Parameters pass checks.')