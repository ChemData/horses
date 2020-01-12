import os
import datetime
import random
import pandas as pd
import numpy as np
import horse_functions as hf
import table_operations as to
import race_functions as rf
import owner_functions as of
import estate
import phenotype as phe
from game_parameters.constants import *


class Game:
    owner = 2

    def __init__(self, start_day, gui=False, restart=True):
        self.day = pd.to_datetime(start_day)
        self.day_increment = 0
        if not gui:
            gui = BasicPrinter(self)
        self.gui = gui
        self.automated = True
        if not restart:
            import game_initializer

    def run_days(self, number, basic=False):
        """Run the simulation for a number of days."""
        for n in range(number):
            self._breed_horses()
            self._deliver_foals()
            self._kill_horses()
            if not basic:
                if random.random() <= RACE_PROBABILITY:
                    if self.automated:
                        self.race(horse_ids='random')
                    else:
                        self._prepare_for_race()
            if self.day_increment % PROPERTY_UPDATE == 0:
                phe.update_properties(dead_too=False)
            hf.heal_horses()

            self.day += datetime.timedelta(1)
            self.day_increment += 1
            self.gui.update_day(self.day)
            self.gui.update_money()

    def _deliver_foals(self):
        command = f"SELECT horse_id, name from horses where due_date = '{str(self.day)}'"
        to_deliver = to.query_to_dataframe(command)
        for _, horse in to_deliver.iterrows():
            if not self.automated:
                name = input(f"{horse['name']} has given birth to a foal. "
                             f"What would you like it name it?")
            else:
                foal_id = hf.give_birth(horse['horse_id'], self.day, name=None)
                self.gui.display_message(
                    f"[horses:{horse['horse_id']}] has given birth to a foal named [horses:{foal_id}].")

    def _kill_horses(self):
        """Kill any horses who are due to die this day."""
        command = f"SELECT horse_id, name from horses where expected_death = '{str(self.day)}'"
        to_kill = pd.read_sql_query(command, to.db)
        for _, horse in to_kill.iterrows():
            self.gui.display_message(f"[horses:{horse['horse_id']}] has died. F.")
            hf.kill_horse(horse['horse_id'], self.day)

    def _prepare_for_race(self):
        """Create a new race and invite the owners to send horses."""
        horses_per_owner = 2

        # Determine the prizes for the race
        total_purse = int(np.random.power(1)*1000)
        purse_1 = int(total_purse * np.random.uniform(0.5, 0.9))
        purse_2 = int((total_purse - purse_1) * np.random.uniform(0.5, 0.9))
        purse_3 = total_purse - purse_1 - purse_2
        purse = (purse_1, purse_2, purse_3)

        # Determine the length
        length = random.choice([1000, 1500, 2000, 2500])

        self.race_info = {'horses_per_owner':horses_per_owner, 'length':length, 'purse':purse}

        # Ask if the player wishes to join
        self.gui.ask_to_join_race(self.race_info)

    def run_race(self, player_horses=[]):
        """Run a race with the provided horses from the player."""
        horses = player_horses.copy()
        for o in of.owner_list():
            if o != self.owner:
                horses += of.pick_race_horses(o, self.race_info['horses_per_owner'])
        self.race(horse_ids=horses, track_length=self.race_info['length'],
                  winnings=self.race_info['purse'])

    def race(self, horse_ids='random', track_length=1000., noisey_speeds=True,
             winnings=(100, 50, 20)):
        """Race the specified horses to see who is the fastest.

        Args:
            horse_ids (list, str): List of int IDs of all horses in the race. If 'random', will
                randomly select some horses to run.
            track_length (float): Length of the track in meters.
            noisey_speeds (bool): If True, will add some gaussian noise to the speed of each horse.
            winnings (tuple): Amount won by the 1st, second, third, etc. horses.

        Return:
            List. Times (in seconds) of each horse involved in the same order as their ids in the
                input.
            List. The numbers of the top 3 finishers.
        """
        if horse_ids == 'random':
            horses = hf.raceable_horses(owner_id=None)
            horse_ids = np.random.choice(horses, 8, replace=False)
        horse_ids = np.array(horse_ids)
        if len(horse_ids) < 1:
            raise ValueError("There must be at least one horse in a race.")

        query = f"SELECT horse_id, speed FROM horse_properties WHERE horse_id in {tuple(horse_ids)}"
        speeds = to.query_to_dataframe(query)['speed'].values
        if noisey_speeds:
            speeds += np.random.normal(0, 1, len(speeds))

        # See if any injuries occur
        for i, horse in enumerate(horse_ids):
            injuries = hf.check_for_injuries(horse, 'race')
            for phrase, v in injuries.items():
                hf.apply_damage(horse, v[0], v[1], self.day)
                self.gui.display_message(f"[horses:{horse}] suffered {phrase}.")
                speeds[i] = 0  # If a horse is injured it cannot run the race.

        with np.errstate(divide='ignore', invalid='ignore'):  # We are ok with dividing by 0
            times = track_length/speeds
        finish_inds = np.argsort(times)
        finish_ids = horse_ids[finish_inds]

        # Update tables to reflect the outcome
        race_id = rf.add_race(self.day, track_length, winnings)

        output = pd.DataFrame()
        output['horse_id'] = horse_ids
        output['time'] = times
        output.sort_values(by=['time'], inplace=True)
        output.index = range(len(output))
        output['place'] = np.arange(len(output)) + 1
        output['winnings'] = 0
        for i, prize in enumerate(winnings):
            if i == len(output):
                break
            output.loc[i, 'winnings'] = prize
        output['race_id'] = race_id
        output.replace(np.inf, np.nan, inplace=True)
        to.insert_dataframe_into_table('race_results', output)

        for i, row in output.iterrows():
            horse_id = int(row['horse_id'])
            winnings = row['winnings']
            if winnings > 0:
                owner = hf.owner_of(horse_id)
                of.add_money(owner, winnings)

        # Format a message for the gui
        msg = f'In a nail bitting finish, the race was won by [horses:{finish_ids[0]}] ({times[finish_inds[0]]:.4} s)'
        try:
            msg += f'<br>[horses:{finish_ids[1]}] came in second with a time of {times[finish_inds[1]]:.4} s.'
        except IndexError:
            pass
        try:
            msg += f'<br>[horses:{finish_ids[2]}] came in' \
                f' third with a time of {times[finish_inds[2]]:.4} s.'
        except IndexError:
            pass
        self.gui.display_message(msg)
        self.gui.update_money()

    def _breed_horses(self):
        if not self.automated:
            return
        options = self.breedable_horses()
        try:
            fem = np.random.choice(options.loc[options['gender'] == 'F', 'horse_id'].values)
            male = np.random.choice(options.loc[options['gender'] == 'M', 'horse_id'].values)
            hf.horse_sex(fem, male, self.day)
        except (ValueError, hf.PregnancyIssue):
            pass

    def str_to_datetime(self, str):
        """Tries to convert a date string to a datetime."""
        return pd.to_datetime(str).to_pydatetime().date()

    def reset(self):
        """Clear databases and reinitialize the starting game settings."""
        to.clear_tables(['horses', 'owners'])

    def random_startup(self):
        """Adds some random data to tables to get the game started."""
        hf.make_random_horses(50, self.day)
        self.add_owners(5, STARTING_MONEY)
        self.estate = estate.Estate(self.owner)

    def simulate_horse_population(self, days):
        """Clear all horses. Create an initial population of 50 horses and let them
        randomly reproduce for days. Then assign all horses to the owners."""
        self.automated = True
        self.reset()
        self.random_startup()
        self.run_days(days, basic=False)
        owners = of.owner_list()
        for h in self.living_horses():
            hf.trade_horse(h, np.random.choice(owners, size=1)[0])
        self.automated = False

    def breedable_horses(self, owner=None):
        """Return an array of horses that can be made to breed.

        Args:
            owner (int or None): The ID of the owner to get available horses for. If None,
                will return horses for all owners.

        """
        youngest = str(self.day - datetime.timedelta(SEXUAL_MATURITY))
        if owner is None:
            command = f"SELECT * FROM horses where" \
                f" death_date is NULL" \
                f" and due_date is NULL" \
                f" and birth_date <= '{youngest}'"
        else:
            command = f"SELECT * FROM horses where" \
                f" owner_id = {owner}" \
                f" and death_date is NULL" \
                f" and due_date is NULL" \
                f" and birth_date <= '{youngest}'"
        horses = to.query_to_dataframe(command)
        horses['age'] = horses['birth_date'].apply(self.display_age)
        return horses[['name', 'horse_id', 'gender', 'age']]

    def display_age(self, birthday):
        """Converts a birthday into an approximate age."""
        age = (self.day - birthday).days
        years = age//365
        months = (age - years*365)//30
        if years == 0:
            return f"{months}m"
        return f"{years}y {months}m"

    def horse_info(self, horse_id):
        """Return formatted information of the desired horse."""
        data = to.get_rows('horses', [horse_id]).iloc[0]
        age = (self.day - data['birth_date']).days
        title = hf.horse_title(data['gender'], age)
        props = to.query_to_dataframe(
            f"SELECT * FROM horse_properties WHERE horse_id = {horse_id}").iloc[0]
        if pd.isna(data['death_date']):
            verb = 'is'
        else:
            verb = 'was'
        msg = f"[horses:{data['horse_id']}] {verb} a {props['base_color']}" \
            f" {title} of age {self.display_age(data['birth_date'])}."

        # Add parent information
        if data['dam'] is None:
            msg += '<body style="text-indent:20px">Dam: Unknown</body>'
        else:
            msg += f'<body style="text-indent:20px">Dam: [horses:{data["dam"]}]</body>'
        if data['sire'] is None:
            msg += '<body style="text-indent:20px">Sire: Unknown</body>'
        else:
            msg += f'<body style="text-indent:20px">Sire: [horses:{data["sire"]}]</body>'

        msg += '<br></br>'

        # Add owner
        msg += f'<body style="text-indent:0px">Owner: {data["owner_id"]}</body>'

        # Add speed
        msg += f'<body style="text-indent:0px">Speed: {props["speed"]:.4}</body>'

        def injury_term(x):
            if x == 0:
                return 'healthy'
            if x <= 25:
                return 'injured'
            if x <= 75:
                return 'seriously injured'
            return 'fucked up'

        # Add injuries
        msg += f'<body style="text-indent:0px">' \
            f'Legs: {injury_term(data["leg_damage"])}</body>'
        msg += f'<body style="text-indent:0px">' \
            f'Ankles: {injury_term(data["ankle_damage"])}</body>'
        msg += f'<body style="text-indent:0px">' \
            f'Heart: {injury_term(data["heart_damage"])}</body>'

        msg += '<br></br>'
        # Add race history
        race_history = hf.race_summary(horse_id).iloc[0]
        msg += f"Total winnings: ${race_history['winnings']:.2f}"
        msg += f"<body style='text-indent:20px'>First places: {race_history[1]}</body>"
        msg += f"<body style='text-indent:20px'>Second places: {race_history[2]}</body>"
        msg += f"<body style='text-indent:20px'>Third places: {race_history[3]}</body>"
        return msg

    def living_horses(self, owner_id=None):
        """Return the ids of all living horses owned by the specified owner.

        Args:
            owner_id (int, None): Owner to find horses of. If None, will return all
                living horses regardless of source.

        Return:
            List. List of all ids of horses owned.
        """
        if owner_id is None:
            command = f"SELECT horse_id from horses WHERE" \
                f" death_date is NULL"
            params = []
        else:
            command = f"SELECT horse_id from horses WHERE" \
                f" owner_id = ?" \
                f" and death_date is NULL"
            params =[owner_id]
        return list(to.query_to_dataframe(command, params=params)['horse_id'].values)

    def add_owners(self, number, starting_cash):
        """Add new owners.

        Args:
            number (int): Number of new owners to add.
            starting_cash (float): How much cash each owner should have.

        Returns:
            None.
        """
        for i in range(1, number+1):
            if i == self.owner:
                of.add_owner(starting_cash, 'Player')
            elif i == 1:
                of.add_owner(0, 'Wild')
            else:
                of.add_owner(starting_cash)


class BasicPrinter:

    def __init__(self, game):
        self.game = game

    def display_message(self, msg):
        print(msg)

    def update_day(self, date):
        print(f"----{str(date)} Dawns----")

    def update_money(self):
        print(f'Cash: ${of.money(self.game.owner)}')

    def ask_to_join_race(self):
        inp = input('Do you want to join an upcoming race?')
        if inp in ['n', 'N']:
            return []
        else:
            return []


#g = Game('20150101')
#g.simulate_horse_population(100)