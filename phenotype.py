import numpy as np
import genetics as ge


"""
Phenotypic system

The goal here is to convert a horse's DNA (genotype) into useful, player-relevant properties
(phenotype). For instance, we want to know how fast a horse will run based on the activity of its
genes.json controlling weight, muscle size, etc.

This model consists of three layers.
1) Genotype. Each horse has two chromosomes consisting of many genes.json. A given allele for a gene
    has an activity level ranging from 0 (inactive) to 1 (very active). Genotype is hard for the
    the player to see/measure.
2) Anatomy. These properties are directly derived from genotype. For instance, heart size, weight,
    muscle twitch speed. Multiple genes.json can determine a single anatomic property and one gene can
    feed into multiple anatomic properties. So, a gene controlling growth hormone production might
    lead to a larger heart size and a higher weight. For ease of later computation, anatomic
    properties are scaled from 0 to 1, often by a sigmoid function. The player has partial access
    to anatomy and may need special equipment to get more information. So, heart size is initially
    found only by autopsy but could be determined in vivo if the player purchased an MRI machine.
    In the future, it would be smart to mix in environmental factors here: random chance, training,
    food quality, etc. [A thought: make it so no anatomic features are directly accesible. Instead,
    if you want the player to be able to access the property, there must be a stat
    which is derived purely from the anatomy. Thus, anatomy properties can always range from 0 to 1
    and stats can always have reasonable real-world scaling. For instance, the heart_size property
    would determine the heart_size stat, the latter of which would range from  3.5 to 4.5 kg.]
3) Stats. These properties are directly derived from anatomy. Stats include speed, acceleration,
    injury probability, etc. They may be derived from one or more anatomic property and one
    anatomic property can influence multiple stats. Stats may initially be scaled from 0 to 1 but
    should be converted into real world values (e.g. speed should be scaled to about 12-17 m/s).
    These will tend to be player measureable properties like height, leg length, etc. Some will,
    however, not be measurable like heart failure probability.
    
A different but related model is used for things like coat color.
1) Genotype. Each horse has two chromosomes consisting of many genes.json. A given allele for a gene
    has an activity level ranging from 0 (inactive) to 1 (very active). If a gene is not inactive,
    the specific genotype form is calculated by dividing the activity range into pieces. For
    instance, If the Agouti gene is inactive it will have genotype form "a". If it is active, its
    activity will range between (0, 1). (0, .25) might yield "At". [0.25, 0.75) might yield "A".
    And [0.75, 1) might yield "A+". The exact ranges would be set separately for each gene.
2) Anatomy. If-then logic takes the genotype to actual attributes. The primary example is coat
    color/pattern. By looking at all the genes.json, we determine what the horse's color/pattern name is
    "Black", 'White", "Cremello", etc.
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

    return non_white_color(ext, agouti, cream, dun, champagne, dapple, flaxen)


def non_white_color(ext, agouti, cream, dun, champagne, dapple, flaxen):
    """Return the basic color name for the horse that is not white.

    Args:
        ext (str): e or E.
        agouti (str): a, At, A, A+.
        cream (str): cr, prl, Cr, CrCr.
        dun (str): d, D.
        champagne (str): ch, Ch.
        dapple (str): z, Z.
        flaxen (str): f, F.

    Returns:
        str. Basic color pattern of the horse.
    """

    if ext == 'E':
        if cream == 'CrCr':
            if champagne == 'Ch':
                if agouti == 'a':
                    return 'classic cream'
                elif agouti == 'At':
                    return 'sable cream'
                else:
                    return 'amber cream'
            else:
                if dapple == 'Z':
                    if dun == 'd':
                        if agouti == 'a':
                            return 'silver smoky cream'
                        elif agouti == 'At':
                            return 'silver seal brown cream'
                        else:
                            return 'silver dapple perlino'
                    else:
                        if agouti == 'a':
                            return 'silver dapple cream grulla'
                        else:
                            return 'silver dapple perlino dun'
                else:
                    if dun == 'd':
                        if agouti == 'a':
                            return 'smoky cream'
                        elif agouti == 'At':
                            return 'seal brown cream'
                        else:
                            return 'perlino'
                    else:
                        if agouti == 'a':
                            return 'cream grulla'
                        else:
                            return 'perlino dun'
        elif cream == 'Cr':
            if champagne == 'Ch':
                if agouti == 'a':
                    return 'classic cream'
                elif agouti == 'At':
                    return 'sable cream'
                else:
                    return 'amber cream'
            else:
                if dapple == 'Z':
                    if dun == 'd':
                        if agouti == 'a':
                            return 'silver dapple'
                        elif agouti == 'At':
                            return 'silver dapple brown'
                        elif agouti == 'A':
                            return 'silver dapple buckskin'
                        elif agouti == 'A+':
                            return 'silver wild buckskin'
                    else:
                        if agouti == 'a':
                            return 'silver dapple grulla'
                        elif agouti == 'At':
                            return 'silver dapple dun'
                        else:
                            return 'silver dapple dunskin'
                else:
                    if dun == 'd':
                        if agouti == 'a':
                            return 'silver dapple'
                        elif agouti == 'At':
                            return 'silver dapple brown'
                        elif agouti == 'A':
                            return 'silver dapple buckskin'
                        elif agouti == 'A+':
                            return 'silver wild buckskin'
                    else:
                        if agouti == 'a':
                            return 'smoky grulla'
                        elif agouti == 'At':
                            return 'brown dun'
                        else:
                            return 'dunskin'
        elif cream == 'prl':
            if champagne == 'Ch':
                if dun == 'd':
                    if dapple == 'Z':
                        return 'silver champagne pearl'
                    else:
                        return 'champagne pearl'
                else:
                    if agouti == 'a':
                        return 'champagne dun pearl'
                    elif agouti == 'At':
                        return 'sable dun pearl'
                    else:
                        return 'amber dun pearl'
            else:
                if dapple == 'Z':
                    if dun == 'd':
                        return 'silver dapple pearl'
                    else:
                        return 'silver dun pearl'
                else:
                    if dun == 'd':
                        return 'pearl'
                    else:
                        return 'dun pearl'
        else:
            if champagne == 'Ch':
                if dun == 'd':
                    if agouti == 'a':
                        name = 'classic champagne'
                    elif agouti == 'At':
                        name = 'sable champagne'
                    else:
                        name = 'amber champagne'
                else:
                    if agouti == 'a':
                        name = 'champagne dun'
                    elif agouti == 'At':
                        name = 'sable dun'
                    else:
                        name = 'amber dun'
                if dapple == 'Z':
                    return 'silver ' + name
                else:
                    return name
            else:
                if dapple == 'Z':
                    if dun == 'd':
                        if agouti == 'a':
                            return 'silver dapple'
                        elif agouti == 'At':
                            return 'silver dapple brown'
                        elif agouti == 'A':
                            return 'silver dapple bay'
                        elif agouti == 'A+':
                            return 'silver dapple wild bay'
                    else:
                        if agouti == 'a':
                            return 'silver dapple grulla'
                        else:
                            return 'silver dapple dun'
                else:
                    if dun == 'd':
                        if agouti == 'a':
                            return 'black'
                        elif agouti == 'At':
                            return 'seal brown'
                        elif agouti == 'A':
                            return 'bay'
                        elif agouti == 'A+':
                            return 'wild bay'
                    else:
                        if agouti == 'a':
                            return 'grulla'
                        elif agouti == 'At':
                            return 'brown dun'
                        else:
                            return 'classic dun'
    else:
        if cream == 'CrCr':
            if champagne == 'Ch':
                return 'gold cream'
            else:
                return 'cremello'
        elif cream == 'Cr':
            if champagne == 'Ch':
                return 'gold cream'
            else:
                if dun == 'D':
                    return 'dunalino'
                else:
                    return 'palomino'
        elif cream == 'prl':
            if champagne == 'Ch':
                if dun == 'D':
                    return 'gold dun pearl'
                else:
                    if flaxen == 'F':
                        return 'champagne pearl'
                    else:
                        return 'flaxen apricot champagne'
            else:
                if dun == 'D':
                    if flaxen == 'F':
                        return 'apricot dun'
                    else:
                        return 'flaxen apricot dun'
                else:
                    if flaxen == 'F':
                        return 'apricot'
                    else:
                        return 'flaxen apricot'
        else:
            if champagne == 'Ch':
                if dun == 'D':
                    return 'gold dun'
                else:
                    if flaxen == 'F':
                        return 'gold champagne'
                    else:
                        return 'flaxen gold champagne'
            else:
                if dun == 'D':
                    if flaxen == 'F':
                        return 'red dun'
                    else:
                        return 'flaxen dun'
                else:
                    if flaxen == 'F':
                        return 'chestnut'
                    else:
                        return 'flaxen chestnut'


def hair_additions(chromo1, chromo2):
    """Return the name of the coat pattern resulting from the addition of hairs resulting
    from the sooty, rabicano, kit, overo, splashed white, and leopard complex genes."""
    # Determine if the horse is white
    kit = [ge.discrete_allele(cr, 'kit') for cr in (chromo1, chromo2)]
    if 'W' in kit:
        return ''

    output = ''

    sooty = 'sty'
    if 'Sty' in [ge.discrete_allele(cr, 'sooty') for cr in (chromo1, chromo2)]:
        sooty = 'Sty'

    rabi = 'rb'
    if 'Rb' in [ge.discrete_allele(cr, 'rabicano') for cr in (chromo1, chromo2)]:
        rabi = 'Rb'

    overo = 'o'
    if 'O' in [ge.discrete_allele(cr, 'overo') for cr in (chromo1, chromo2)]:
        overo = 'O'

    splash = 'Spl'
    if 'spl' in [ge.discrete_allele(cr, 'splashed') for cr in (chromo1, chromo2)]:
        splash = 'spl'

    sabino = 'sb'
    if 'Sb' in kit:
        sabino = 'Sb'

    roan = 'rn'
    if 'Rn' in kit:
        roan = 'Rn'

    tabino = 'tb'
    if 'Tb' in kit:
        tabino = 'Tb'

    leopard = 'LpLp'
    ls = [ge.discrete_allele(cr, 'leopard_complex') for cr in (chromo1, chromo2)]
    if 'lp' in ls:
        if 'Lp' not in ls:
            leopard = 'lp'
        else:
            leopard = 'Lp'

    p1 = 'patn1'
    if 'PATN1' in [ge.discrete_allele(cr, 'pattern1') for cr in (chromo1, chromo2)]:
        p1 = 'PATN1'

    p2 = 'patn2'
    if 'PATN2' in [ge.discrete_allele(cr, 'pattern2') for cr in (chromo1, chromo2)]:
        p2 = 'PATN2'


def kit_phenotype(chromo1, chromo2):
    """Return the phenotype generated by the KIT gene."""
    kits = [ge.discrete_allele(cr, 'kit') for cr in (chromo1, chromo2)]


# Anatomic properties

def weight(chromo1, chromo2):
    a1, _, _ = ge.activity_level(chromo1, 'size')
    a2, _, _ = ge.activity_level(chromo2, 'size')
    ave = (a1+a2)/2
    return ave


def muscle_mass(chromo1, chromo2):
    a1, _, _ = ge.activity_level(chromo1, 'size')
    a2, _, _ = ge.activity_level(chromo2, 'size')
    size = (a1+a2)/2

    a1, _, _ = ge.activity_level(chromo1, 'muscle_strength')
    a2, _, _ = ge.activity_level(chromo2, 'muscle_strength')
    strength = (a1+a2)/2

    return (size + 2 * strength)/3


def heart_size(chromo1, chromo2):
    a1, _, _ = ge.activity_level(chromo1, 'heart_growth')
    a2, _, _ = ge.activity_level(chromo2, 'heart_growth')
    size = (a1+a2)/2

    return size


def tendon_strength(chromo1, chromo2):
    a1, _, _ = ge.activity_level(chromo1, 'connective_strength')
    a2, _, _ = ge.activity_level(chromo2, 'connective_strength')
    strength = (a1+a2)/2

    return strength


# Stats

def speed(chromo1, chromo2):
    """Return the speed in m/s"""
    mm = muscle_mass(chromo1, chromo2)
    w = weight(chromo1, chromo2)
    hs = heart_size(chromo1, chromo2)

    return 13 + 2*mm - w + hs


def weight_stat(chromo1, chromo2):
    """Return the weight in kg."""

    return 450 + 100 * weight(chromo1, chromo2)


def injury_risk(chromo1, chromo2):
    """Return the probability of injury in a single race."""
    return max(0, muscle_mass(chromo1, chromo2) - tendon_strength(chromo1, chromo2)) * 0.05


def heart_failure(chromo1, chromo2):
    """Return the probability of heart failure in a single race."""
    return heart_size(chromo1, chromo2) ** 4 * 0.05


def sigmoid(x):
    return 1/(1+np.exp(-x))
