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
import game_calendar
import game_parameters.constants as c


class Game:
    wild = 1  # owner_id of unowned horses
    owner = 2  # owner_id of the player
    default_start_day = '20000101' #  Start date to use if one hadn't been saved

    def __init__(self, start_day, gui=False, restart=True):
        if not gui:
            gui = BasicPrinter(self)
        self.gui = gui
        self.automated = True
        if restart:
            to.create_empty_tables(True)

        self._read_game_info()
        self.god_mode = False

    def run_days(self, number, basic=False):
        """Run the simulation for a number of days."""
        for n in range(number):
            self._deliver_foals()
            self._kill_horses()
            self._run_events()
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
            if self.day_increment % 2 == 0:
                self._ai_sell_extra_horses()
                self._ai_breed_horses()
            self._conduct_healing()
            self._train_horses()

            if self.day.date().month == 12 and self.day.date().day == 31:
                game_calendar.put_events_on_calendar(self.day.date().year+1)

            self.day += datetime.timedelta(1)
            self.day_increment += 1
            self.gui.update_day(self.day)
            self.gui.update_money()

    def generate_history(self, number_of_days, number_of_starting_horses):
        """
        Simulate horse history by breeding, racing, and killing horses.
        Args:
            number_of_days (int): How many days of history to simulate.
            number_of_starting_horses (int): How many horses to start with.

        Returns:
            None.
        """
        hf.make_random_horses(number_of_starting_horses, self.day)
        self.automated = True
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
        self.automated = False

        for i in range(30):
            ef.generate_employee()

        # Set up the player's starting estate
        self.add_owners(5, c.STARTING_MONEY)
        estate.add_estate(self.owner, replace=True)
        estate.buy_land(self.owner, c.INIT_ESTATE_SIZE, for_free=True)
        estate.add_building(self.owner, 'small_stable', True)
        estate.add_building(self.owner, 'cottage', True)

        self._redistribute_horses()

        game_calendar.put_events_on_calendar(self.day.date().year)

        self.gui.update_money()
        self.gui.update_day(self.day)

    def _redistribute_horses(self):
        """Redistributes living horses among the players."""
        # Start by returning all horses to the wild
        to.cursor.execute("UPDATE horses SET owner_id = ?", [self.wild])

        # And then give the human player as many horses as they deserve
        living = np.array(self.living_horses())
        np.random.shuffle(living)
        for i in range(c.HUMAN_STARTING_HORSES):
            hf.trade_horse(living[i], self.owner)

        # And the AI players get the rest
        horses_per_ai = (len(living) - c.HUMAN_STARTING_HORSES)//len(self.ai_owners)
        offset = c.HUMAN_STARTING_HORSES
        for i, owner_id in enumerate(self.ai_owners):
            for horse in range(horses_per_ai):
                hf.trade_horse(living[offset], owner_id)
                offset += 1

    def load_saved(self, name):
        """Use an existing database for this game."""
        to.load_save(name)
        self._read_game_info()
        self.gui.update_day(self.day)
        self.gui.update_money()
        self.automated = False

    def save_game(self, name):
        """Save the database for this game."""
        # The game state information has to be saved
        d = pd.DataFrame({'date': self.day, 'date_increment': self.day_increment}, index=[0])
        d.to_sql('game_info', to.db, if_exists='replace', index=False)

        # Save the database
        to.save_game(name)

    def _deliver_foals(self):
        command = f"SELECT horse_id, name, owner_id from horses where due_date = '{str(self.day)}'"
        to_deliver = to.query_to_dataframe(command)
        for _, horse in to_deliver.iterrows():
            if horse['owner_id'] == self.owner:
                foal_info = hf.give_birth(horse['horse_id'], self.day,store_horse=False)
                name = self.gui.ask_to_name_foal(horse['name'], foal_info['gender'])
                foal_info['name'] = name
                foal_id = hf.add_horse(foal_info)
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

    def _prepare_for_race(self, horses_for_player=1, racers=10, purse='random',
                          name='random', length='random', track='dirt', speed_bonus=0.0,
                          **kwargs):
        """
        Create a new race and invite the owners to send horses.
        Args:
            horses_for_player (int): Number of horses the player is allowed to send.
            racers (int): Total number of horses participating.
            purse (list, 'random'): The amount that the winners will earn. If 'random,
                will generate a random purse.
            name (str): Name of the race. If 'random', will use a random race name.
            length (float, 'random'): Length of the race (in meters). If 'random, will use
                a random track length.
            track (str): Material of the track.
            speed_bonus (float): How much of a speed boost to give to non-player horses
                (in m/s). A negative value will slow those horses down.

        Returns:
            None.
        """
        # Determine the prizes for the race
        if purse == 'random':
            total_purse = int(np.random.power(1)*1000)
            purse_1 = int(total_purse * np.random.uniform(0.5, 0.9))
            purse_2 = int((total_purse - purse_1) * np.random.uniform(0.5, 0.9))
            purse_3 = total_purse - purse_1 - purse_2
            purse = (purse_1, purse_2, purse_3)

        # Determine a name for the race
        if name == 'random':
            start = random.choice(['Santa Anita', 'Rhineland', 'American', 'Royal',
                                   'Sussex', 'Alameda', 'Atlanta', 'Champions'])
            end = random.choice(['Stakes', 'Invitational', 'Derby', 'Cup', 'Classic',
                                 'Handicap', 'International', 'Sprint', 'Memorial'])
            name = f'{start} {end}'

        # Determine the length
        if length == 'random':
            length = random.choice([1000, 1500, 2000, 2500])

        self.current_race = {'purse': purse, 'length': length, 'name': name,
                             'horses_for_player': horses_for_player, 'racers': racers,
                             'track': track, 'speed_bonus': speed_bonus}

        # Ask if the player wishes to join
        self.gui.ask_to_join_race()

    def run_race(self, player_horses=()):
        """Run a race with the provided horses from the player."""
        horses = list(player_horses)
        horses_needed = self.current_race['racers'] - len(player_horses)
        owner_picks = np.random.choice(self.ai_owners, horses_needed)
        for o in self.ai_owners:
            number = np.sum(owner_picks == o)
            horses += of.pick_race_horses(o, number)
        self.race(horse_ids=horses, track_length=self.current_race['length'],
                  winnings=self.current_race['purse'], speed_bonus=self.current_race['speed_bonus'])

    def race(self, horse_ids='random', track_length=1000., noisey_speeds=True,
             winnings=(100, 50, 20), allow_injuries=True, speed_bonus=0):
        """Race the specified horses to see who is the fastest.

        Args:
            horse_ids (list, str): List of int IDs of all horses in the race. If 'random', will
                randomly select some horses to run.
            track_length (float): Length of the track in meters.
            noisey_speeds (bool): If True, will add some gaussian noise to the speed of each horse.
            winnings (tuple): Amount won by the 1st, second, third, etc. horses.
            allow_injuries (bool): If True, will allow horses to get injured during the race.
            speed_bonus (float): How much additional speed to give to the AI horses.

        Return:
            List. Times (in seconds) of each horse involved in the same order as their ids in the
                input.
            List. The numbers of the top 3 finishers.
        """
        if horse_ids == 'random':
            horses = hf.raceable_horses(owner_id=None)
            horse_ids = np.random.choice(horses, 8, replace=False)
        horse_ids = np.array(horse_ids)
        if len(horse_ids) < len(winnings):
            self.gui.display_message("The race was canceled because there were too few horses.")
            return
        if len(horse_ids) < 1:
            raise ValueError("There must be at least one horse in a race.")

        qry = f"""
                SELECT 
                    p.horse_id, 
                    p.speed, 
                    h.owner_id 
                FROM 
                    horse_properties p
                LEFT JOIN horses h ON
                    p.horse_id = h.horse_id
                WHERE
                    p.horse_id in {tuple(horse_ids)}"""
        speeds = to.query_to_dataframe(qry)
        speeds.loc[speeds['owner_id'] != self.owner, 'speed'] += speed_bonus
        if noisey_speeds:
            speeds['speed'] += np.random.normal(0, 1, len(speeds))

        # See if any injuries occur
        if allow_injuries:
            for i, horse in enumerate(horse_ids):
                is_injured = self._injure_horse(horse, 'race')
                if is_injured:
                    speeds.loc[i, 'speed'] = 0  # An injured horse cannot run

        with np.errstate(divide='ignore', invalid='ignore'):  # We are ok with dividing by 0
            speeds['time'] = track_length/speeds['speed']
        speeds.sort_values(by='speed', ascending=False, inplace=True)
        speeds.index = range(len(speeds))

        # Update tables to reflect the outcome
        race_id = rf.add_race(self.day, track_length, winnings)

        speeds['place'] = range(1, len(speeds)+1)
        speeds['race_id'] = race_id
        speeds['winnings'] = 0
        speeds.loc[:len(winnings)-1, 'winnings'] = winnings
        speeds.replace(np.inf, np.nan, inplace=True)

        for i, row in speeds.iterrows():
            prize = row['winnings']
            if prize > 0:
                of.add_money(int(row['owner_id']), prize)

        del speeds['owner_id']
        del speeds['speed']
        to.insert_dataframe_into_table('race_results', speeds)

        # Format a message for the gui
        h1 = speeds.iloc[0]
        msg = f'In a nail bitting finish, the race was won by [horses:{int(h1["horse_id"])}]' \
              f' ({h1["time"]:.4} s)'
        try:
            h2 = speeds.iloc[1]
            msg += f'<br>[horses:{int(h2["horse_id"])}] came in second with a time of {h2["time"]:.4} s.'
        except IndexError:
            pass
        try:
            h3 = speeds.iloc[2]
            msg += f'<br>[horses:{int(h3["horse_id"])}] came in' \
                f' third with a time of {h3["time"]:.4} s.'
        except IndexError:
            pass
        self.gui.display_message(msg)
        self.gui.update_money()

    def _breed_wild_horses(self):
        """Breed wild horses randomly to achieve a growth rate."""
        pop_growth = 0.008  # monthly population growth. Corresponds to about 10% annual
        pregnancies = math.ceil(pop_growth * len(self.living_horses()))
        options = self.breedable_horses()
        if pregnancies == 0 or len(options[options['gender'] == 'F']) == 0:
            return
        fems = np.random.choice(
            options.loc[options['gender'] == 'F', 'horse_id'].values, pregnancies, replace=False)
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
        if estate.building_count(self.owner, 'track') > 0:
            speed = f"{props['speed']:.4} m/s"
        else:
            speed = 'unknown'
        msg += f'<body style="text-indent:0px">Speed: {speed}</body>'

        # Add weight
        if estate.building_count(self.owner, 'scale') > 0:
            weight = f"{props['weight_stat']:.4} kg"
        else:
            weight = 'unknown'
        msg += f'<body style="text-indent:0px">Weight: {weight}</body>'

        # Add heart size
        if estate.building_count(self.owner, 'mri') > 0:
            hsize = f"{props['heart_size']:.4}/1"
        else:
            hsize = 'unknown'
        msg += f'<body style="text-indent:0px">Heart Size: {hsize}</body>'

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
        estate.buy_land(self.owner, 1000000, for_free=True)
        estate.add_building(self.owner, 'lodge', for_free=True)
        estate.add_building(self.owner, 'lodge', for_free=True)
        estate.add_building(self.owner, 'lodge', for_free=True)
        estate.add_building(self.owner, 'lodge', for_free=True)
        estate.add_building(self.owner, 'large_stable', for_free=True)
        estate.add_building(self.owner, 'large_stable', for_free=True)
        estate.add_building(self.owner, 'large_stable', for_free=True)
        estate.add_building(self.owner, 'large_stable', for_free=True)
        self.gui.update_money()
        self.god_mode = True

    def _ai_sell_extra_horses(self):
        """Have the AI sell horses above a certain threshold.

        The current heuristic is to sell the horses with the lowest speed.
        """
        for owner_id in self.ai_owners:
            q = """
            SELECT horse_properties.horse_id, speed FROM horse_properties \
                INNER JOIN horses ON horse_properties.horse_id = horses.horse_id
                WHERE horses.owner_id = ? AND horses.death_date is NULL
                ORDER BY speed DESC
            """
            to_sell = to.query_to_dataframe(q, [owner_id]).iloc[20:]
            of.add_money(owner_id, len(to_sell) * c.MEAT_PRICE)
            for i, horse in to_sell.iterrows():
                hf.trade_horse(horse['horse_id'], self.wild)

    def _ai_breed_horses(self):
        """Have the AI breed good horses together.

        The current heuristic is to breed all males with the fastest stallions. The
        probability of a stallion breeding is given by a boltzmann distribution.
        """
        youngest = str(self.day - datetime.timedelta(c.SEXUAL_MATURITY))
        for owner_id in self.ai_owners:
            q = """
            SELECT horse_properties.horse_id, speed, gender FROM horse_properties \
                INNER JOIN horses ON horse_properties.horse_id = horses.horse_id
                    WHERE horses.owner_id = ?
                    AND horses.death_date is NULL
                    AND horses.due_date is NULL
                    AND horses.birth_date < ?
                ORDER BY speed DESC
            """
            to_breed = to.query_to_dataframe(q, [owner_id, youngest])
            ladies = to_breed[to_breed['gender'] == 'F']
            men = to_breed[to_breed['gender'] == 'M'].copy()
            if len(ladies) == 0 or len(men) == 0:
                continue
            men['speed'] -= men['speed'].min()
            men['prob'] = men['speed'].apply(lambda x: math.e**(x/.2))
            men['prob'] /= men['prob'].sum()
            bred_men = np.random.choice(men['horse_id'].values, size=len(ladies), p=men['prob'])
            for i, lady_id in enumerate(ladies['horse_id'].values):
                hf.horse_sex(lady_id, bred_men[i], self.day)

    @property
    def ai_owners(self):
        """Return the ids of the ai owners."""
        return list(set(of.owner_list()).difference([self.owner, self.wild]))

    def _read_game_info(self):
        """Read the saved game info into instance variables if it is available."""
        info = to.game_info_state()
        if info is None:
            self.day = pd.to_datetime(self.default_start_day)
            self.day_increment = 0
        else:
            self.day = pd.to_datetime(info['date'])
            self.day_increment = info['date_increment']

    def _run_events(self):
        """Run any events which are due to happen on the current day."""

        qry = f"SELECT * FROM calendar WHERE date=?"
        events = to.query_to_dataframe(qry, params=[game_calendar.as_sql_date(self.day)])
        for i, event in events.iterrows():
            info = c.EVENTS[event['name']]
            if event['type'] == 'race':
                self._prepare_for_race(horses_for_player=1, **info)
            else:
                self.gui.display_message(f"There is an event scheduled for today ({info['name']}),"
                                         f"but there is no code to execute for it.")


class Race:
    """This class holds the information for a single upcoming race including distance,
    purse, conditions, racers, etc. Then, can run the race and update the appropriate
    tables with the results."""

    def __init__(self, length='random', name='random', track='dirt', horses_for_player=1,
                 racers=10, purse='random', speed_bonus=0.0):
        """
        Args:
            length (float, 'random'): Length of the race (in meters). If 'random, will use
                a random track length.
            name (str): Name of the race. If 'random', will use a random race name.
            track (str): Material of the track.
            horses_for_player (int): Number of horses the player is allowed to send.
            racers (int): Total number of horses participating.
            purse (list, 'random'): The amount that the winners will earn. If 'random,
                will generate a random purse.
            speed_bonus (float): How much of a speed boost to give to non-player horses
                (in m/s). A negative value will slow those horses down.
        """
        # Determine the prizes for the race
        if purse == 'random':
            total_purse = int(np.random.power(1)*1000)
            purse_1 = int(total_purse * np.random.uniform(0.5, 0.9))
            purse_2 = int((total_purse - purse_1) * np.random.uniform(0.5, 0.9))
            purse_3 = total_purse - purse_1 - purse_2
            purse = (purse_1, purse_2, purse_3)

        # Determine a name for the race
        if name == 'random':
            start = random.choice(['Santa Anita', 'Rheinland', 'American', 'Royal',
                                   'Sussex', 'Alameda', 'Atlanta', 'Champions'])
            end = random.choice(['Stakes', 'Invitational', 'Derby', 'Cup', 'Classic',
                                 'Handicap', 'International', 'Sprint', 'Memorial'])
            name = f'{start} {end}'

        # Determine the length
        if length == 'random':
            length = random.choice([1000, 1500, 2000, 2500])

        self.length = length
        self.purse = purse
        self.name = name
        self.track = track
        self.horses_for_player = horses_for_player
        self.racers = racers
        self.speed_bonus = speed_bonus


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