from math import floor
import pandas as pd
import owner_functions as of
import employee_functions as ef
import table_operations as to
from game_parameters.constants import *

"""
Estates
    
    Estates are where owners keep, train, and care for their horses. Estates have a size
which can be increased by buying more land. Buildings can be built on the estate to do
useful things. Building stables increases the number of horses that can be kept on the
estate. Any land that is not used for buildings, is considered pasture. Each horse needs
a certain amount of pasture to live.

Currently only the player has an estate. In the future, the AI players should get them as
well.
"""


def add_estate(owner, replace=False):
    """
    Add an estate for an owner.
    Args:
        owner (int): ID of the owner.
        replace (bool): If True, will replace the existing estate that the owner has.

    Returns:
        None.
    """
    d = to.query_to_dataframe(f"SELECT owner_id FROM estates WHERE owner_id=?", params=[owner])
    if len(d) > 0:
        if not replace:
            return
        else:
            to.db.execute(f"DELETE FROM estates WHERE owner_id=?", [owner])
    to.insert_into_table('estates', {'owner_id': owner})


def add_building(owner, building_name, for_free=False):
    """
    Add a building to the estate of an owner.

    Args:
        owner (int): The ID of the owner who owns the estate.
        building_name (str): Name of the building to add.
        for_free (bool): If True, will add the building without deducting the money.
    """
    # Check for available land
    if BUILDINGS[building_name]['size'] > free_land(owner):
        raise NotEnoughLand(
            f"There is not enough room on the estate for a {building_name}.")

    # Check for money
    if not for_free:
        cost = BUILDINGS[building_name]['cost']
        try:
            of.remove_money(owner, cost)
        except ValueError:
            raise InsufficientFunds(
                f"Owner-{owner} can't afford that building ($ {cost}).")

    # Add the building
    qry = f"UPDATE estates SET {building_name} = {building_name} + 1 WHERE owner_id = ?"
    to.cursor.execute(qry, [owner])

    # Remove the land
    sell_land(owner, BUILDINGS[building_name]['size'], for_free=True)

    # Commit the changes
    to.db.commit()


def remove_building(owner, building_name):
    """
        Remove a building from the estate.

        If the building is not present, a ValueError will be thrown.
        Args:
            owner (int): ID of the owner selling the building.
            building_name (str): Name of the building to remove.

        Return:
            None.
    """
    qry = f"SELECT {building_name} FROM estates WHERE owner_id = ?"
    count = to.query_to_dataframe(qry, [owner]).loc[0, building_name]
    if count > 0:
        # Remove the building
        qry = f"UPDATE estates SET {building_name} = ? WHERE owner_id = ?"
        to.cursor.execute(qry, [max(0, count-1), owner])

        # Remove the land
        sell_land(owner, BUILDINGS[building_name]['size'], for_free=True)

        # Commit the changes
        to.db.commit()
    else:
        raise ValueError(f"The building {building_name} is not present in the estate.")


def free_land(owner):
    """
    Return the amount of free land on the estate of the owner.
    Args:
        owner (int): ID of owner of the estate.

    Returns:
        float. How many hectares of free land exist on the estate.
    """
    qry = "SELECT free_land FROM estates WHERE owner_id = ?"
    d = to.cursor.execute(qry, [owner]).fetchall()
    if len(d) == 0:
        return 0
    else:
        return d[0][0]


def buy_land(owner, amount, for_free=False):
    """
    Add land to a player and make them pay for it.
    Args:
        owner (int): ID of the owner buying the land.
        amount (float): Number of acres of land to buy.
        for_free (bool): If True, won't deduct money.

    Returns:
        None.
    """
    # Check for money
    if not for_free:
        cost = amount * LAND_COST
        try:
            of.remove_money(owner, cost)
        except ValueError:
            raise InsufficientFunds(
                f"Owner-{owner} can't afford to purchase $ {cost} worth of land.")
    qry = f"""
        UPDATE estates 
            SET 
                free_land = free_land + ?,
                total_land = total_land + ?
        WHERE
            owner_id = ?;"""
    to.cursor.execute(qry, [amount, amount, owner])
    to.db.commit()


def sell_land(owner, amount, for_free=False):
    """
    Sell free land from an owner's estate.

    Args:
        owner (int): ID of the owner selling the land.
        amount (float): Amount of land to sell.
        for_free (bool): If True, won't add money.
    """
    # Check for free land
    if amount > free_land(owner):
        raise NotEnoughLand('The Estate does not have enough free land to sell.')
    qry = f"""
        UPDATE estates 
            SET 
                free_land = free_land - ?,
                total_land = total_land - ?
        WHERE
            owner_id = ?;"""
    to.cursor.execute(qry, [amount, amount, owner])
    if not for_free:
        of.add_money(owner, amount * LAND_COST)
    to.db.commit()


def stable_capacity(owner):
    """
    Return the number of horses that the estate can stable.

    Args:
        owner (int): ID of the owner of the estate.

    Returns:
        int. Number of horses that can fit in the stables.
    """
    d = to.query_to_dataframe("SELECT * FROM estates WHERE owner_id = ?", params=[owner])
    out = 0
    for col, val in d.iloc[0].items():
        try:
            out += BUILDINGS[col].get('horse_capacity', 0) * val
        except KeyError:
            pass
    return out


def horse_capacity(owner):
    """Return the number of horses that the estate can support with both stables
    and pasture."""
    return min(stable_capacity(owner), floor(free_land(owner) / PASTURE_AMT))


def employee_capacity(owner):
    """Return the number of employees that the estate can support."""
    """
    Return the number of horses that the estate can stable.

    Args:
        owner (int): ID of the owner of the estate.

    Returns:
        int. Number of horses that can fit in the stables.
    """
    d = to.query_to_dataframe("SELECT * FROM estates WHERE owner_id = ?", params=[owner])
    if len(d) == 0:
        return 0
    out = 0
    for col, val in d.iloc[0].items():
        try:
            out += BUILDINGS[col].get('person_capacity', 0) * val
        except KeyError:
            pass
    return out


def rooms_available(owner):
    """Return the number of free rooms available for new employees to live in."""
    total = employee_capacity(owner)
    emp = to.query_to_dataframe(
        "SELECT employee_id FROM employees WHERE employer = ?", [owner])
    return total - len(emp)


def building_count(owner, building_type):
    """
    Return the number of buildings of a type that the owner owns.
    Args:
        owner (int): ID of the owner.
        building_type (str): Name of the building.

    Returns:
        int. Number of buildings.
    """
    d = to.query_to_dataframe(
        f"SELECT {building_type} FROM estates WHERE owner_id = ?", params=[owner])
    if len(d) == 0:
        return 0
    return d.iloc[0][building_type]


class InsufficientFunds(Exception):
    """Is raised when the estate-affecting action costs more than the estate owner can
    afford."""


class NotEnoughLand(Exception):
    """Is raised when the estate-affecting action would require more free land than the
     estate has."""

