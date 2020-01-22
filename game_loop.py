import os
import shutil
import datetime
import random
import math
import pandas as pd
import numpy as np
import horse_functions as hf
import table_operations as to
import race_functions as rf
import owner_functions as of
import employee_functions as ef
import estate
import phenotype as phe
import game_parameters.constants as c
import game_initializer


class Game:
    wild = 1  # owner_id of unowned horses
    owner = 2  # owner_id of the player

    def __init__(self, start_day, gui=False, restart=True):
        self.day = pd.to_datetime(start_day)
        self.day_increment = 0
        if not gui:
            gui = BasicPrinter(self)
        self.gui = gui
        self.automated = True
        if restart:
            game_initializer.create_empty_tables()
            to.load_disk_database('game_data.db')
            self.add_owners(5, c.STARTING_MONEY)
        self.estate = estate.Estate(self.owner)
        self.god_mode = False

    def run_days(self, number, basic=False):
        """Run the simulation for a number of days."""
        for n in range(number):
            self._breed_horses()
            self._deliver_foals()
            self._kill_horses()
            if not basic:
                if random.random() <= c.RACE_PROBABILITY:
                    if self.automated:
                        self.race(horse_ids='random')
                    else:
                        self._prepare_for_race()
            if self.day_increment % c.PROPERTY_UPDATE == 0:
                phe.update_properties(dead_too=False)
            if self.day_increment % 7 == 0:
                self._pay_employees()
            self._conduct_healing()
            self._train_horses()

            self.day += datetime.timedelta(1)
            self.day_increment += 1
            self.gui.update_day(self.day)
            self.gui.update_money()

    def generate_history(self, number_of_days):
        """
        Simulate horse history by breeding, racing, and killing horses.
        Args:
            number_of_days (int): How many days of history to simulate.
            number_of_starting_horses (int): How many horses to start with.

        Returns:
            None.
        """
        for n in range(number_of_days):
            self._deliver_foals()
            self._kill_horses()
            if self.day_increment % c.PROPERTY_UPDATE == 0:
                phe.update_properties(dead_too=False)
            if self.day_increment % 30 == 0:
                self._breed_wild_horses()
                # The number of races to permit each horse about 1 race per year
                for i in range(math.ceil(len(self.living_horses())/12/8)):
                    self.race(horse_ids='random', allow_injuries=False)

            self.day += datetime.timedelta(1)
            self.day_increment += 1

    def random_startup(self, days=0):
        """Adds some random data to tables to get the game started."""
        hf.make_random_horses(50, self.day)
        self.generate_history(days)
        for i in range(30):
            ef.generate_employee()
        owners = of.owner_list()
        for h in self.living_horses():
            hf.trade_horse(h, np.random.choice(owners, size=1)[0])
        self.automated = False

    def load_saved(self, name):
        """Use an existing database for this game."""
        to.load_disk_database('20yr_start_game_data.db')
        self.day = pd.to_datetime('20100101')

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
             winnings=(100, 50, 20), allow_injuries=True):
        """Race the specified horses to see who is the fastest.

        Args:
            horse_ids (list, str): List of int IDs of all horses in the race. If 'random', will
                randomly select some horses to run.
            track_length (float): Length of the track in meters.
            noisey_speeds (bool): If True, will add some gaussian noise to the speed of each horse.
            winnings (tuple): Amount won by the 1st, second, third, etc. horses.
            allow_injuries (bool): If True, will allow horses to get injured during the race.

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
        if allow_injuries:
            for i, horse in enumerate(horse_ids):
                is_injured = self._injure_horse(horse, 'race')
                if is_injured:
                    speeds[i] = 0  # An injured horse cannot run

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

    def _breed_wild_horses(self):
        """Breed wild horses randomly to achieve a growth rate."""
        pop_growth = 0.008  # monthly population growth. Corresponds to about 10% annual
        pregnancies = math.ceil(pop_growth * len(self.living_horses()))
        options = self.breedable_horses()
        fems = np.random.choice(
            options.loc[options['gender'] == 'F', 'horse_id'].values, pregnancies, replace=False)
        if len(fems) == 0:
            return
        for fem in fems:
            male = np.random.choice(options.loc[options['gender'] == 'M', 'horse_id'].values)
            try:
                hf.horse_sex(fem, male, self.day)
            except (ValueError, hf.PregnancyIssue):
                pass

    def str_to_datetime(self, str):
        """Tries to convert a date string to a datetime."""
        return pd.to_datetime(str).to_pydatetime().date()

    def reset(self):
        """Clear databases and reinitialize the starting game settings."""
        to.clear_tables(['horses', 'owners'])

    def breedable_horses(self, owner=None):
        """Return an array of horses that can be made to breed.

        Args:
            owner (int or None): The ID of the owner to get available horses for. If None,
                will return horses for all owners.

        """
        youngest = str(self.day - datetime.timedelta(c.SEXUAL_MATURITY))
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

    def _pay_employees(self):
        """Attempt to pay employees their salary. If unable, they will quit."""

        salary = ef.total_salary(self.owner)
        try:
            of.remove_money(self.owner, salary)
            self.gui.display_message(f"Payday! Your happy employees take home ${salary}")
        except ValueError:
            self.gui.display_message("You cannot pay your employees. They quit en masse.")
            command = "UPDATE employees SET employer = ? WHERE employer = ?"
            to.cursor.execute(command, [ef.UNEMPLOYED, self.owner])
            of.remove_money(self.owner, 'all')

    def _conduct_healing(self):
        """
        Heal horses and apply any bonuses resulting from employees.
        Returns:
            None.
        """
        for owner in of.owner_list():
            if owner == self.owner:
                hf.heal_horses(owner_id=owner, heal_rate=ef.employee_bonus(owner, 'heal_rate')+c.HEAL_RATE)
            else:
                hf.heal_horses(owner_id=owner)

    def _train_horses(self):
        """
        Add (or subtract) from all the horses' training.
        Returns:
            None.
        """
        for owner in of.owner_list():
            if owner == self.owner:
                hf.train_horses(owner_id=owner, training_amount=ef.employee_bonus(owner, 'training_rate')-c.TRAINING_DECAY)
            else:
                hf.train_horses(owner_id=owner, training_amount=c.AI_TRAINING-c.TRAINING_DECAY)

    def _injure_horse(self, horse_id, event):
        """
        Check to see if a horse is injured in an event, and then apply the damage.
        Args:
            horse_id (int): ID of the horse to injure.
            event (str): Name of the event the horse is doing (e.g. 'race').
        Returns:
            Bool. True, if the horse is injured at all. False, otherwise.
        """
        owner = hf.owner_of(horse_id)
        injuries = hf.check_for_injuries(horse_id, event)
        injury_reduction = ef.employee_bonus(owner, 'major_injury_reduction')
        for injury in injuries:
            inj_info = c.INJURIES[event][injury]
            # See if the injury can be reduced
            reduced = False
            try:
                new_inj = inj_info['reduces_to']
                if random.random() <= injury_reduction:
                    reduced = True
                    new_inj_info = c.INJURIES[event][new_inj]
                    self.gui.display_message(
                        f"[horses:{horse_id}] has suffered {new_inj_info['display']}"
                        f" (reduced from {inj_info['display']}).")
                    hf.apply_damage(
                        horse_id, new_inj_info['part'], new_inj_info['damage'], self.day)
            except KeyError:
                pass
            if not reduced:
                self.gui.display_message(f"[horses:{horse_id}] has suffered {inj_info['display']}.")
                hf.apply_damage(
                    horse_id, inj_info['part'], inj_info['damage'], self.day)
        if len(injuries) > 0:
            return True
        return False

    def enable_god_mode(self):
        """Give the player bonuses and powers that are useful for debugging."""
        of.add_money(self.owner, 10000000)
        self.estate.buy_land(1000000, for_free=True)
        self.estate.add_building('lodge', for_free=True)
        self.estate.add_building('lodge', for_free=True)
        self.estate.add_building('lodge', for_free=True)
        self.estate.add_building('lodge', for_free=True)
        self.estate.add_building('large_stable', for_free=True)
        self.estate.add_building('large_stable', for_free=True)
        self.estate.add_building('large_stable', for_free=True)
        self.estate.add_building('large_stable', for_free=True)
        self.gui.update_money()
        self.god_mode = True


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