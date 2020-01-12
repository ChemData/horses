import genetics as ge


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