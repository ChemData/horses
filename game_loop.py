import os
import datetime
import random
import pandas as pd
import numpy as np
import horse_functions as hf
import table_operations as to
import race_functions as rf
import owner_functions as of
import game_initializer
import phenotype


class Game:
    owner = 2

    def __init__(self, start_day, gui=False):
        self.day = pd.to_datetime(start_day)
        if not gui:
            gui = BasicPrinter()
        self.gui = gui
        self.automated = True

    def run_days(self, number, basic=False):
        """Run the simulation for a number of days."""
        for n in range(number):
            self._deliver_foals()
            self._kill_horses()
            if not basic:
                if random.random() >= .1:
                    self._prepare_for_race()
            self.day += datetime.timedelta(1)
            self.gui.update_day(self.day)
            self.gui.update_money()

    def _deliver_foals(self):
        command = f"SELECT id, name from horses where due_date = '{str(self.day)}'"
        to_deliver = pd.read_sql_query(command, to.db)
        for _, horse in to_deliver.iterrows():

            if not self.automated:
                name = input(f"{horse['name']} has given birth to a foal. "
                             f"What would you like it name it?")
            else:
                name = np.random.choice(hf.HORSE_NAMES)
                foal_id = hf.give_birth(horse['id'], self.day, name)
                self.gui.display_message(
                    f"[horses:{horse['id']}] has given birth to a foal named [horses:{foal_id}].")

    def _kill_horses(self):
        """Kill any horses who are due to die this day."""
        command = f"SELECT id, name from horses where expected_death = '{str(self.day)}'"
        to_kill = pd.read_sql_query(command, to.db)
        for _, horse in to_kill.iterrows():
            self.gui.display_message(f"[horses:{horse['id']}] has died. F.")
            hf.kill_horse(horse['id'], self.day)

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
            horses = self.living_horses(self.owner)
            horse_ids = np.random.choice(horses, 8, replace=False)
        horse_ids = np.array(horse_ids)
        if len(horse_ids) < 1:
            raise ValueError("There must be at least one horse in a race.")

        speeds = []
        for id in horse_ids:
            speeds += [hf.speed(id)]
        speeds = np.array(speeds)
        if noisey_speeds:
            speeds += np.random.normal(0, 1, len(speeds))
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
            fem = np.random.choice(options.loc[options['gender'] == 'F'].index)
            male = np.random.choice(options.loc[options['gender'] == 'M'].index)
            hf.horse_sex(fem, male, self.day)
        except ValueError:
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
        self.add_owners(5, 1000)

    def simulate_horse_population(self, days):
        """Clear all horses. Create an initial population of 50 horses and let them
        randomly reproduce for days. Then assign all horses to the owners."""
        self.automated = True
        self.reset()
        self.random_startup()
        self.run_days(days, basic=True)
        owners = of.owner_list()
        for h in self.living_horses():
            hf.trade_horse(h, np.random.choice(owners, size=1)[0])
        self.automated = False

    def breedable_horses(self):
        """Return an array of horses that can be made to breed."""
        youngest = str(self.day - datetime.timedelta(hf.VALS['SEXUAL_MATURITY']))
        command = f"SELECT * FROM horses where" \
            f" owner_id = {self.owner}" \
            f" and death_date is NULL" \
            f" and due_date is NULL" \
            f" and birth_date <= '{youngest}'"
        horses = to.query_to_dataframe(command)
        horses['age'] = horses['birth_date'].apply(self.display_age)
        return horses[['name', 'id', 'gender', 'age']]

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
        color = hf.coat(horse_info=data)
        if data['death_date'] is None:
            verb = 'is'
        else:
            verb = 'was'
        msg = f"[horses:{data['id']}] {verb} a {color} {title} of age {self.display_age(data['birth_date'])}."

        # Add parent information
        if data['dam'] is None:
            msg += '<p style="text-indent:20px">Dam: Unknown</p>'
        else:
            msg += f'<p style="text-indent:20px">Dam: [horses:{data["dam"]}]</p>'
        if data['sire'] is None:
            msg += '<p style="text-indent:20px">Sire: Unknown</p>'
        else:
            msg += f'<p style="text-indent:20px">Sire: [horses:{data["sire"]}]</p>'

        # Add speed
        msg += f'<p style="text-indent:20px">Speed: {hf.speed(horse_info=data):.4}</p>'

        # Add owner
        msg += f'<p style="text-indent:20px">Owner: {data["owner_id"]}</p>'

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
            command = f"SELECT id from horses WHERE" \
                f" death_date is NULL"
        else:
            command = f"SELECT id from horses WHERE" \
                f" owner_id = {owner_id}" \
                f" and death_date is NULL"
        return list(pd.read_sql_query(command, to.db)['id'].values)

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