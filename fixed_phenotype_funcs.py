import genetics as ge
import unsaved_phenotype as up

"""
The functions of this file are all anatomic properties derived from genes. They never need to be
recalculated. By only calculating them when needed and then storing the result performance should
remain good even for large numbers of horses.

There is a table which stores the output of all these functions. When a value is needed for a
horse, the table is checked. If a row has not been calculated for that horse they will be calculated
and added.

The table column names are the same as the function names here. The table is the same as the one
used for recalc_phenotype_funcs.
"""

# Coat colors
def base_color(chromo1, chromo2):
    # Determine if the horse is white
    kit = [ge.discrete_allele(cr, 'kit') for cr in (chromo1, chromo2)]
    if 'W' in kit:
        return 'white'

    # Find the base color and the main fadings/dilutions
    ext = 'e'
    if 'E' in [ge.discrete_allele(cr, 'extension') for cr in (chromo1, chromo2)]:
        ext = 'E'

    agouti = [ge.discrete_allele(cr, 'agouti') for cr in (chromo1, chromo2)]
    if 'A+' in agouti:
        agouti = 'A+'
    elif 'A' in agouti:
        agouti = 'A'
    elif 'At' in agouti:
        agouti = 'At'
    else:
        agouti = 'a'

    cream = [ge.discrete_allele(cr, 'cream') for cr in (chromo1, chromo2)]
    if 'Cr' in cream and 'cr' not in cream:
        cream = 'CrCr'
    elif 'Cr' in cream:
        cream = 'Cr'
    elif 'prl' in cream and 'cr' not in cream:
        cream = 'prl'
    else:
        cream = 'cr'

    dun = 'd'
    if 'D' in [ge.discrete_allele(cr, 'dun') for cr in (chromo1, chromo2)]:
        dun = 'D'

    champagne = 'ch'
    if 'Ch' in [ge.discrete_allele(cr, 'champagne') for cr in (chromo1, chromo2)]:
        champagne = 'Ch'

    dapple = 'z'
    if 'Z' in [ge.discrete_allele(cr, 'dapple') for cr in (chromo1, chromo2)]:
        dapple = 'Z'

    flaxen = 'f'
    if 'F' in [ge.discrete_allele(cr, 'flaxen') for cr in (chromo1, chromo2)]:
        flaxen = 'F'

    return up.non_white_color(ext, agouti, cream, dun, champagne, dapple, flaxen)


