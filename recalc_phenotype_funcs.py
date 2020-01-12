import genetics as ge

"""
The functions of this file are all anatomic properties derived from genes. They do not need to be
recalculated frequently. (At this point they do not need to be recalculated at all but I plan on
adding a significant age component to some which will necessitate recalculation). Recalculating them
only as needed, and at most, say, once a month should keep performance manageable as the number of
horses grows.

There is a database which stores the output of all these functions. When a value is needed for a
horse, the table is checked. If a row has not been calculated for that horse, or the values are
older than, say, 1 month [definable in the parameters], they will be calculated and added. Values
are only updated as needed.

The table column names are the same as the function names here.
"""

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


# Injury modifiers

def knee_injury(chromo1, chromo2):
    """Return the risk multiplier of a knee injury.

    Risk is increased if muscle mass is larger than tendon strength, and vice versa.

    Ranges from .1 to 10
    """
    mm = muscle_mass(chromo1, chromo2)
    ts = tendon_strength(chromo1, chromo2)
    return (mm*.9+.1)/(ts*.9+.1)  # Magic numbers scale the output from .1 to 10


def heart_failure(chromo1, chromo2):
    """Return the risk multiplier of heart failure in a single race.

    Ranges from 1 to 10.
    """

    hs = heart_size(chromo1, chromo2)
    if hs < .5:
        return 1
    return (hs**4 - 0.0625)*9.6 + 1  # Magic numbers scale the output from 1 to 10
