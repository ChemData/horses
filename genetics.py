import hashlib
import numpy as np
from game_parameters.constants import *


"""Genetics System.

This system is a simplified model of inheritance, mutation, gene expression, and physiology loosely
informed by actual biology. It does not attempt to replicate the way that living things work but
merely the flavor of evolution.

Some ideas and terminology:

Chromosome - Each animal has two chromosome, one from their father, one from their mother. A 
    chromosome is a string of fixed length.
Gene - Each chromosome is composed of genes.json. Every gene is 6 characters long. All characters in a
    chomosome are part of a gene: there is no non-transcribing material.
Base pair - Each character can be thought of as a base pair. The base pairs are the numbers 0-9.
Allele - A particular sequence of base pairs for a gene. Each allele will behave differently in
    an animal. Some will work better than others.
Well Formed - In the real world not all sequences of DNA will lead to aminoacid sequences which
    turn into usable proteins. In this model not all alleles are well formed. If they are not well
    formed, the activity level is set to 0.
Activity Level - Well formed alleles will produce different activity levels. This is analogous to
    different alleles yielding different phenotypes.
Genotype form - For certain genes.json (like coat color genetics) we don't want a numerical 
    activity level. Instead we want to know an allele code. For instance, if the Agouti gene is
    misformed it will be a. If it is well formed it can be At, A, or A+.
"""


def apply_hash(input_string):
    r = hashlib.md5()
    r.update(input_string.encode('utf-8'))
    return int(r.hexdigest(), 16)


def activity_level(chromosome, gene_name):
    """Return the activity level for the allele of the provided gene in the chromosome.

    Args:
        chromosome (str): Chromosome containing the allele to determine activity level for.
        gene_name (str): Name of the gene of this allele.

    Return:
        Float. Activity level for the allele ranging from 0 to 1. Set to 0 if it is not
            well-formed.
        Float. Raw activity level for the allele ranging from 0 to 1.
        Bool. True if the gene is well formed.
    """
    cutoff = GENES[gene_name].get('cutoff', DEFAULT_WELL_FORMED_CUTOFF)
    allele = get_gene(chromosome, gene_name)
    if cutoff > 1 or cutoff < 0:
        raise ValueError("Gene well-formed cutoff must be between 0 and 1, inclusive.")
    hashed = apply_hash(allele + str(gene_name))
    if (hashed % 100)/100 > cutoff:
        well_formed = True
    else:
        well_formed = False

    hashed = apply_hash(allele)
    activity = (hashed % 100 + 1.)/100

    if well_formed:
        return activity, activity, well_formed
    else:
        return 0., activity, well_formed


def mutate(chromosome, mutation_rate):
    """Introduce substitution errors into a chromosome at the provided rate.

    Args:
        chromosome (str): Genetic material to mutate.
        mutation_rate (float): Probability of mutating each character from 0 to 1 inclusive.

    Return:
        Str. A new chromosome with mutations introduced.
    """
    if mutation_rate > 1 or mutation_rate < 0:
        raise ValueError("The chromosome mutation rate must be between 0 and 1, inclusive.")
    chromosome = np.array(list(chromosome)).astype(int)
    mutate = np.random.choice([0, 1], size=len(chromosome), p=[1-mutation_rate, mutation_rate])
    mutations = np.random.randint(0, 10, len(chromosome))
    chromosome[mutate == 1] = mutations[mutate == 1]
    return ''.join(chromosome.astype(str))


def mix_chromosomes(chromo1, chromo2):
    """Mix the two chromosomes of an individual into a single new chromosome.

    Args:
        chromo1 (str): First chromosome.
        chromo2 (str): Second chromosome.

    Return:
        Str. A chromosome string which a mixture of the alleles in the two originals.
    """
    output = ''
    choices = np.random.randint(0, 2, CHROMOSOME_LENGTH)
    for i in range(CHROMOSOME_LENGTH):
        if choices[i] == 0:
            output += chromo1[i * GENE_LENGTH:(i + 1) * GENE_LENGTH]
        else:
            output += chromo2[i * GENE_LENGTH:(i + 1) * GENE_LENGTH]
    return output


def get_gene(chromosome, gene_name):
    """Return the requested gene from the provided chromosome."""
    try:
        position = GENES[gene_name]['pos']
        return chromosome[position*GENE_LENGTH: (position+1)*GENE_LENGTH]
    except KeyError:
        raise ValueError(f"The gene, {gene_name}, does not exist.")


def random_chromosome():
    """Return a random chromosome."""
    return ''.join(str(elem) for elem in np.random.randint(0, 10, GENE_LENGTH*CHROMOSOME_LENGTH))


def discrete_allele(chromosome, gene_name):
    """Interpret a gene into discrete alleles.

    Args:
        chromosome (str): Chromosome containing the allele to determine allele for.
        gene_name (str): Name of the gene of this allele.

    Return:
        str. Name of the allele.
    """
    gene = GENES[gene_name]

    try:
        gene['alleles']
    except KeyError:
        raise ValueError(f'The gene, {gene_name}, cannot be interpreted discretely.'
                         f' Either add some specific allele codes or interpret using'
                         f' activity_level.')

    cutoff = gene.get('cutoff', DEFAULT_WELL_FORMED_CUTOFF)
    allele = get_gene(chromosome, gene_name)
    if cutoff > 1 or cutoff < 0:
        raise ValueError("Gene well-formed cutoff must be between 0 and 1, inclusive.")
    hashed = apply_hash(allele + str(gene_name))

    if (hashed % 100)/100 < cutoff:
        return gene['broken']

    hashed = apply_hash(allele)
    activity = (hashed % 100 + 1.)/100

    return gene['alleles'][np.sum(activity >= np.array(gene.get('ranges', [])))]

