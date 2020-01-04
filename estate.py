from math import floor
import owner_functions as of

try:
    from game_parameters.local_constants import *
except ModuleNotFoundError:
    from game_parameters.constants import *

"""
Estates
    
    Estates are where owners keep, train, and care for their horses. Estates have a size
which can be increased by buying more land. Buildings can be built on the estate to do
useful things. Building stables increases the number of horses that can be kept on the
estate. Any land that is not used for buildings, is considered pasture. Each horse needs
a certain amount of pasture to live.
"""


class Estate:

    def __init__(self, owner):
        self.owner = owner
        self.size = INIT_ESTATE_SIZE
        self.buildings = []
        self.building_count = {}

    def add_building(self, building_name, for_free=False):
        """Add a building to the estate.

        Args:
            building_name (str): Name of the building to add.
            for_free (Bool): If True, will add the building without deducting the money.
        """
        # Check for available land
        if BUILDINGS[building_name]['size'] > self.pasture_land:
            raise NotEnoughLand(
                f"There is not enough room on the estate for a {building_name}.")

        # Check for money
        if not for_free:
            cost = BUILDINGS[building_name]['cost']
            try:
                of.remove_money(self.owner, cost)
            except ValueError:
                raise InsufficientFunds(
                    f"Owner-{self.owner} can't afford that building ($ {cost}).")
        self.buildings += [building_name]
        self.building_count[building_name] = self.building_count.get(building_name, 0) + 1

    def remove_building(self, building_name):
        """Remove a building from the estate.

        If the building is not present, a ValueError will be thrown.

        Args:
            building_name (str): Name of the building to remove.
        """

        try:
            self.buildings.remove(building_name)
            self.building_count[building_name] -= 1
        except ValueError:
            raise ValueError(f"The building {building_name} is not present in the estate.")

    def buy_land(self, amount, for_free=False):
        """Purchase land for the estate.

        Args:
            amount (float): Amount of land to purchase.
            for_free (Bool): If True, will add the land without deducting the money.
        """
        # Check for money
        if not for_free:
            cost = amount * LAND_COST
            try:
                of.remove_money(self.owner, cost)
            except ValueError:
                raise InsufficientFunds(
                    f"Owner-{self.owner} can't afford to purchase $ {cost} worth of land.")
        self.size += amount

    def sell_land(self, amount):
        """Sell free land from the estate.

        Args:
            amount (float): Amount of land to sell.
        """
        # Check for free land
        if amount > self.pasture_land:
            raise NotEnoughLand('The Estate does not have enough free land to sell.')
        self.size -= amount
        of.add_money(self.owner, amount * LAND_COST)

    @property
    def stable_capacity(self):
        """Return the number of horses that the estate can stable."""
        return sum(BUILDINGS[x].get('horse_capacity', 0) for x in self.buildings)

    @property
    def horse_capacity(self):
        """Return the number of horses that the estate can support with both stables
        and pasture."""
        return min(self.stable_capacity, floor(self.pasture_land/PASTURE_AMT))

    @property
    def employee_capacity(self):
        """Return the number of employees that the estate can support."""
        return sum(BUILDINGS[x].get('person_capacity', 0) for x in self.buildings)

    @property
    def pasture_land(self):
        """Return the number of hectares available for pasturing horses."""
        return self.size - sum(BUILDINGS[x].get('size', 0) for x in self.buildings)


class InsufficientFunds(Exception):
    """Is raised when the estate-affecting action costs more than the estate owner can
    afford."""


class NotEnoughLand(Exception):
    """Is raised when the estate-affecting action would require more free land than the
     estate has."""

