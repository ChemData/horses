import sys
import os
import re
import numpy as np
from PyQt5 import QtWidgets, uic, QtCore, QtGui
from PyQt5.QtWidgets import QApplication, QMessageBox, QMdiSubWindow, QLabel, QWidget, QPushButton,\
    QFrame, QScrollArea, QFileDialog
from game_loop import Game
import table_operations as to
import owner_functions as of
import horse_functions as hf
import employee_functions as ef
import estate
import text_operations as text
from game_parameters.constants import *


class MainScreen(QtWidgets.QMainWindow):
    max_messages = 20  # maximum number of messages to display in the message box

    def __init__(self):
        self.app = QApplication(sys.argv)
        super(MainScreen, self).__init__()
        uic.loadUi(os.path.join('ui_files', 'main_screen.ui'), self)
        self.messages = []

        self.game = Game('19900101', gui=self)

        self._setup_sub_windows()

        self.input_connect()
        self.show()

        sys.exit(self.app.exec())

    def _setup_sub_windows(self):
        self.currently_showing_box = None

        self.race_window = RaceWindow(self, self.game)
        self.pedigree_window = PedigreeWindow(self, self.game)
        self.property_window = PropertyWindow(self, self.game)

        self.breeding_box = BreedingBox(self, self.game)
        self.mdi.addSubWindow(self.breeding_box)

        self.trading_box = TradeBox(self, self.game)
        self.mdi.addSubWindow(self.trading_box)

        self.building_box = BuildingBox(self, self.game)
        self.mdi.addSubWindow(self.building_box)

        self.employee_box = EmployeeBox(self, self.game)
        self.mdi.addSubWindow(self.employee_box)

    def input_connect(self):
        self.next_day.clicked.connect(self._next_day_push)
        self.next_n_days.clicked.connect(self._next_n_days_push)
        self.day_amount_entry.valueChanged.connect(self._change_n_days_text)
        self.message_box.anchorClicked.connect(self.display_link_info)
        self.entity_info_box.anchorClicked.connect(self.display_link_info)
        self.actionBreeding.triggered.connect(self._show_breeding_box)
        self.actionTrading.triggered.connect(self._show_trading_box)
        self.actionPedigree.triggered.connect(self._show_pedigree_window)
        self.actionBuildings.triggered.connect(self._show_building_box)
        self.actionEmployees.triggered.connect(self._show_employee_box)
        self.actionHorse_Properties.triggered.connect(self._show_property_window)
        self.actionQuick.triggered.connect(lambda x: self.game.generate_history(0, 25))
        self.action10_Year.triggered.connect(lambda x: self.game.generate_history(10*365, 25))
        self.action20_Year.triggered.connect(lambda x: self.game.generate_history(20*365, 25))
        self.actionLoad.triggered.connect(self._load_game)
        self.actionSave.triggered.connect(self._save_game)
        self.actionGod_mode.triggered.connect(self.game.enable_god_mode)

    def _next_day_push(self):
        self.game.run_days(1)

    def _next_n_days_push(self):
        self.game.run_days(self.day_amount_entry.value())

    def _change_n_days_text(self):
        days = self.day_amount_entry.value()
        if days == 1:
            self.next_n_days.setText(f'Play 1 Day')
        else:
            self.next_n_days.setText(f'Play {days} Days')

    def update_day(self, date):
        self.day_display.setText(f'{date.date()}')

    def update_money(self):
        money = of.money(self.game.owner)
        self.money_display.setText(f'Cash: ${money}')

    def _show_breeding_box(self):
        try:
            self.currently_showing_box.hide()
        except AttributeError:
            pass
        self.breeding_box.show()
        self.breeding_box.update()
        self.currently_showing_box = self.breeding_box

    def _show_trading_box(self):
        try:
            self.currently_showing_box.hide()
        except AttributeError:
            pass
        self.trading_box.show()
        self.trading_box.update()
        self.currently_showing_box = self.trading_box

    def _show_building_box(self):
        try:
            self.currently_showing_box.hide()
        except AttributeError:
            pass
        self.building_box.show()
        self.building_box.update()
        self.currently_showing_box = self.building_box

    def _show_employee_box(self):
        try:
            self.currently_showing_box.hide()
        except AttributeError:
            pass
        self.employee_box.show()
        self.employee_box.update()
        self.currently_showing_box = self.employee_box

    def _show_pedigree_window(self):
        self.pedigree_window.show()

    def _show_property_window(self):
        self.property_window.show()

    def display_link_info(self, url):
        """Display information about the thing that was just clicked on. Also show
        information in the pedigree window if it is open."""
        _, entity_type, id_ = url.toString().split('#')
        id_ = int(id_)
        if entity_type == 'horses':
            info = self.game.horse_info(id_)
            if self.pedigree_window.isVisible():
                self.pedigree_window.update(id_)
            if self.property_window.isVisible():
                self.property_window.update(id_)
        else:
            info = ''
        info = convert_to_links(info)
        self.entity_info_box.setText(info)

    def display_message(self, msg, clear=False):
        """Display an update in the main window."""
        if clear:
            self.messages = []
        msg = convert_to_links(msg)
        msg = f'<body>{self.game.day}: </body>' + msg
        self.messages = [msg] + self.messages
        if len(self.messages) > self.max_messages:
            self.messages.pop(-1)

        total_message = '<body>------------------</body><br></br>'.join(self.messages)
        self.message_box.setText(total_message)

    def ask_to_join_race(self, race_info):
        reply = QMessageBox.question(
            self, 'PyQt5 message', "Do you want to enter horses in the upcoming race?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.race_window.show()
            self.race_window.update(race_info)
            return []
        else:
            self.game.run_race(player_horses=[])

    def ask_to_name_foal(self, mother, foal_gender):
        nw = NamingDialog(self, mother, foal_gender)
        nw.exec()
        return nw.name_entry.toPlainText()

    def show_list_horse_info(self, t):
        """Display the information of a horse in the list."""
        info = self.game.horse_info(t.horse_id)
        info = convert_to_links(info)
        self.entity_info_box.setText(info)

    def _load_game(self):
        """Ask the player to select a saved game to load."""
        filename, _ = QFileDialog.getOpenFileName(self, "Select a saved game to load", "saves")
        if filename is not None:
            self.game.load_saved(filename)

    def _save_game(self):
        """Ask the player where they want to save the game."""
        filename, _ = QFileDialog.getSaveFileName(self, "Select a file to save as", "saves")
        if filename is not None:
            self.game.save_game(filename)


class BreedingBox(QMdiSubWindow):

    def __init__(self, main_screen, game):
        self.main = main_screen
        self.game = game
        super(BreedingBox, self).__init__()
        uic.loadUi(os.path.join('ui_files', 'breed_box.ui'), self)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        self.input_connect()
        self.hide()

    def update(self):
        self._populate_breeding_lists()

    def _populate_breeding_lists(self):
        """Add available horses to the list of mares and sires to breed."""
        horses = self.main.game.breedable_horses(self.game.owner)
        self.dam_selection.clear()
        for i, dam in horses[horses['gender'] == 'F'].iterrows():
            item = QtWidgets.QListWidgetItem()
            item.horse_id = dam['horse_id']
            item.setData(0, f"{dam['name']}")
            self.dam_selection.insertItem(1, item)

        self.sire_selection.clear()
        for i, sire in horses[horses['gender'] == 'M'].iterrows():
            item = QtWidgets.QListWidgetItem()
            item.horse_id = sire['horse_id']
            item.setData(0, f"{sire['name']}")
            self.sire_selection.insertItem(1, item)

    def input_connect(self):
        self.dam_selection.itemClicked.connect(self.main.show_list_horse_info)
        self.sire_selection.itemClicked.connect(self.main.show_list_horse_info)
        self.breed_button.clicked.connect(self._breed)

    def _display_link_info(self, url):
        """Display information about the thing that was just clicked on."""
        _, entity_type, id_ = url.toString().split('#')
        id_ = int(id_)
        if entity_type == 'horses':
            info = self.game.horse_info(id_)
        else:
            info = ''
        info = convert_to_links(info)
        self.entity_info_box.setText(info)

    def _show_list_horse_info(self, t):
        """Display the information of a horse in the race list."""
        info = self.game.horse_info(t.horse_id)
        info = convert_to_links(info)
        self.game.entity_info_box.setText(info)

    def _breed(self):
        """Breed the selected horses."""
        try:
            dam = self.dam_selection.selectedItems()[0]
        except:
            self.main.display_message("A dam must be selected for breeding.")
            return
        try:
            sire = self.sire_selection.selectedItems()[0]
        except:
            self.main.display_message("A sire must be selected for breeding.")
            return
        hf.horse_sex(dam.horse_id, sire.horse_id, self.game.day)
        self.main.display_message(f"{dam.text()} and {sire.text()} have bred.")
        self.update()


class RaceWindow(QtWidgets.QMainWindow):

    def __init__(self, main_screen, game):
        self.main = main_screen
        self.game = game
        super(RaceWindow, self).__init__()
        uic.loadUi(os.path.join('ui_files', 'race_screen.ui'), self)

        self.input_connect()

    def update(self, race_info):
        self._refresh_horse_list()
        self.horses_needed = race_info['horses_per_owner']
        msg_text = f'Track Length: {race_info["length"]} m'
        msg_text += '\nPurse Distribution'
        for i, p in enumerate(race_info['purse']):
            msg_text += f'\n\t{text.ordinal(i+1)} place: ${p:.2f}'
        self.race_info.setText(msg_text)
        self._update_number_needed()

    def _refresh_horse_list(self):
        self.horse_selection.clear()
        self.race_horses.clear()
        for h in hf.raceable_horses(self.game.owner):
            item = QtWidgets.QListWidgetItem()
            item.horse_id = h
            name = to.get_rows('horses', [h])['name'].values[0]
            item.setData(0, f"{name}")
            self.horse_selection.insertItem(1, item)

    def input_connect(self):
        self.entity_info_box.anchorClicked.connect(self._display_link_info)
        self.horse_selection.itemDoubleClicked.connect(self._add_horse_to_race)
        self.horse_selection.itemClicked.connect(self._show_list_horse_info)
        self.race_horses.itemDoubleClicked.connect(self._remove_horse_from_race)
        self.race_horses.itemClicked.connect(self._show_list_horse_info)
        self.race_begin_button.clicked.connect(self._send_horses_to_race)
        self.cancel_button.clicked.connect(self._cancel)

    def _display_link_info(self, url):
        """Display information about the thing that was just clicked on."""
        _, entity_type, id_ = url.toString().split('#')
        id_ = int(id_)
        if entity_type == 'horses':
            info = self.game.horse_info(id_)
        else:
            info = ''
        info = convert_to_links(info)
        self.entity_info_box.setText(info)

    def _show_list_horse_info(self, t):
        """Display the information of a horse in the race list."""
        info = self.game.horse_info(t.horse_id)
        info = convert_to_links(info)
        self.entity_info_box.setText(info)

    def _add_horse_to_race(self, horse):
        """Add a horse from the horse list to the race list."""
        horse = self.horse_selection.takeItem(self.horse_selection.row(horse))
        self.race_horses.addItem(horse)
        self._update_number_needed()

    def _remove_horse_from_race(self, horse):
        """Remove a horse from the race list."""
        horse = self.race_horses.takeItem(self.race_horses.row(horse))
        self.horse_selection.addItem(horse)
        self._update_number_needed()

    def _update_number_needed(self):
        """Determine how many horses have been selected and update the number needed text."""
        selected = self.race_horses.count()
        diff = self.horses_needed - selected
        if diff == 0:
            self.number_to_pick.setText('Selection Complete')
            self.race_begin_button.setEnabled(True)
        elif diff > 0:
            self.number_to_pick.setText(f'Select {diff} More')
            self.race_begin_button.setDisabled(True)
        elif diff < 0:
            self.number_to_pick.setText(f'Remove {-1*diff} From Selection')
            self.race_begin_button.setDisabled(True)

    def _send_horses_to_race(self):
        ids = [self.race_horses.item(x).horse_id for x in range(self.race_horses.count())]
        self.game.run_race(player_horses=ids)
        self.hide()

    def _cancel(self):
        self.game.run_race(player_horses=[])
        self.hide()


class TradeBox(QMdiSubWindow):
    def __init__(self, main_screen, game):
        self.main = main_screen
        self.game = game
        super(TradeBox, self).__init__()
        uic.loadUi(os.path.join('ui_files', 'trade_box.ui'), self)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        self.input_connect()
        self.hide()

        # Set the starting selections
        self.my_horse = None
        self.their_horses = {}
        self.counterparty = 2

    def input_connect(self):
        self.horse_selection.itemClicked.connect(self.main.show_list_horse_info)
        self.horse_selection.itemClicked.connect(self._keep_horse_selection)
        self.counterparty_selection.currentIndexChanged.connect(self._populate_horse_list)
        self.counterparty_selection.currentIndexChanged.connect(self._keep_counterparty_selection)
        self.buy_radio.toggled.connect(self._populate_horse_list)
        self.sell_radio.toggled.connect(self._populate_horse_list)
        self.send_offer_button.clicked.connect(self._offer)

    def update(self):
        self._populate_horse_list()
        self._populate_owner_list()
        self._set_selected_counterparty()
        self._set_selected_horse()

    def _populate_horse_list(self):
        """Add available horses to the list."""
        counterparty = self.counterparty_selection.currentData()
        if self.sell_radio.isChecked():
            owner_id = self.game.owner
            self.horse_selection_label.setText('Your Horses')
            if counterparty == 1:
                self.price_entry.setText(str(MEAT_PRICE))
                self.price_entry.setEnabled(False)
        else:
            owner_id = counterparty
            self.horse_selection_label.setText('Their Horses')
        self.horse_selection.clear()
        if owner_id != 1:
            horse_ids = self.main.game.living_horses(owner_id)
            for horse in horse_ids:
                name = to.get_column('horses', 'name', horse).iloc[0]['name']
                item = QtWidgets.QListWidgetItem()
                item.horse_id = horse
                item.setData(0, name)
                self.horse_selection.insertItem(1, item)
        if counterparty != 1:
            self.price_entry.setEnabled(True)

        self._set_selected_horse()

    def _display_link_info(self, url):
        """Display information about the thing that was just clicked on."""
        _, entity_type, id_ = url.toString().split('#')
        id_ = int(id_)
        if entity_type == 'horses':
            info = self.game.horse_info(id_)
        else:
            info = ''
        info = convert_to_links(info)
        self.entity_info_box.setText(info)

    def _show_list_horse_info(self, t):
        """Display the information of a horse in the race list."""
        info = self.game.horse_info(t.horse_id)
        info = convert_to_links(info)
        self.entity_info_box.setText(info)

    def _offer(self):
        """Offer to trade the horse for the stated amount."""
        price = self.price_entry.toPlainText()
        try:
            price = round(float(price))
        except ValueError:
            self.main.display_message("That ain't a number!")
            return
        try:
            horse = self.horse_selection.selectedItems()[0].horse_id
        except IndexError:
            self.main.display_message("You gotta select a horse, partner.")
            return

        buying = self.buy_radio.isChecked()
        if self.game.god_mode:
            counterparty = self.counterparty_selection.currentData()
            if buying:
                hf.trade_horse(horse, self.game.owner)
                of.add_money(counterparty, price)
            else:
                hf.trade_horse(horse, counterparty)
                of.add_money(self.game.owner, price)
            self.main.display_message("Some strange power compels me to accept your offer.")
            self.main.update_money()
            self.update()
            return

        if buying and estate.horse_capacity(self.game.owner) <\
                len(self.game.living_horses(self.game.owner)) + 1:
            self.main.display_message("Your estate cannot fit any more horses.")
            return

        if buying and price > of.money(self.game.owner):
            self.main.display_message("You don't have that much money and debt hasn't been implemented.")
            return

        counterparty = self.counterparty_selection.currentData()

        # If you are selling to the general public, the offer is always accepted
        if counterparty == self.game.wild:
            decision = 'yes'
        else:
            decision = of.evaluate_trade(counterparty, horse, price, self.main.game.day, not buying)
        if decision == 'soft no':
            self.main.display_message("I'm afraid I can't afford that.")
        elif decision == 'no':
            if buying:
                self.main.display_message("You'll have to offer more than that.")
            elif not buying:
                self.main.display_message("You've got to be kidding me! I ain't paying that"
                                          " much for a bag o' bones.")
        elif decision == 'yes':
            self.main.display_message(f"You've got yourself a deal!")
            if self.sell_radio.isChecked():
                hf.trade_horse(horse, counterparty)
                of.add_money(self.game.owner, price)
                if counterparty != self.game.wild:
                    of.remove_money(counterparty, price)
            else:
                hf.trade_horse(horse, self.game.owner)
                of.add_money(counterparty, price)
                of.remove_money(self.game.owner, price)
        self.main.update_money()
        self.update()
        return

    def _populate_owner_list(self):
        """Put owner names in the owner selection dropdown."""
        self.counterparty_selection.clear()
        for i, row in to.get_column('owners', 'name').iterrows():
            if row['owner_id'] != self.game.owner:
                item = QtWidgets.QListWidgetItem()
                item.owner_id = row['owner_id']
                item.setData(0, row['name'])
                self.counterparty_selection.blockSignals(True)
                if item.owner_id == self.game.wild:
                    self.counterparty_selection.addItem('Abattoir', userData=row['owner_id'])
                else:
                    self.counterparty_selection.addItem(row['name'], userData=row['owner_id'])
                self.counterparty_selection.blockSignals(False)

    def _keep_horse_selection(self, t):
        """Store which horse was selected so that it can be recalled later."""
        buying = self.buy_radio.isChecked()
        if not buying:
            self.my_horse = self.horse_selection.currentRow()
        else:
            self.their_horses[self.counterparty_selection.currentIndex()] =\
                self.horse_selection.currentRow()

    def _set_selected_horse(self):
        """Set the currently selected horse based on what had been previously selected."""
        if self.buy_radio.isChecked():
            try:
                self.horse_selection.setCurrentRow(
                    self.their_horses[self.counterparty_selection.currentIndex()])
            except KeyError:
                pass
        else:
            try:
                self.horse_selection.setCurrentRow(self.my_horse)
            except TypeError:
                pass

    def _keep_counterparty_selection(self, t):
        """Store which counterparty was selected so that it can be recalled later."""
        if t != -1:
            self.counterparty = t

    def _set_selected_counterparty(self):
        """Set the currently selected counterparty to what it was previously."""
        if self.counterparty is not None:
            self.counterparty_selection.setCurrentIndex(self.counterparty)


class PedigreeWindow(QtWidgets.QMainWindow):

    def __init__(self, main_screen, game):
        self.main = main_screen
        self.game = game
        super(PedigreeWindow, self).__init__()
        uic.loadUi(os.path.join('ui_files', 'pedigree_screen.ui'), self)

        self.input_connect()

    def update(self, horse):
        boxes = [self.f, self.m, self.ff, self.fm, self.mf, self.mm, self.fff, self.ffm,
                 self.fmf, self.fmm, self.mff, self.mfm, self.mmf, self.mmm]
        for box in boxes:
            box.setText('')
        pedigree = hf.pedigree(horse, max_depth=3)
        if pedigree['sire'] is not None:
            a1 = pedigree['sire']
            self.f.setText(a1['name'])
            if a1['sire'] is not None:
                a2 = a1['sire']
                self.ff.setText(a2['name'])
                if a2['sire'] is not None:
                    a3 = a2['sire']
                    self.fff.setText(a3['name'])
                if a2['dam'] is not None:
                    a3 = a2['dam']
                    self.ffm.setText(a3['name'])
            if a1['dam'] is not None:
                a2 = a1['dam']
                self.fm.setText(a2['name'])
                if a2['sire'] is not None:
                    a3 = a2['sire']
                    self.fmf.setText(a3['name'])
                if a2['dam'] is not None:
                    a3 = a2['dam']
                    self.fmm.setText(a3['name'])

        if pedigree['dam'] is not None:
            a1 = pedigree['dam']
            self.m.setText(a1['name'])
            if a1['sire'] is not None:
                a2 = a1['sire']
                self.mf.setText(a2['name'])
                if a2['sire'] is not None:
                    a3 = a2['sire']
                    self.mff.setText(a3['name'])
                if a2['dam'] is not None:
                    a3 = a2['dam']
                    self.mfm.setText(a3['name'])
            if a1['dam'] is not None:
                a2 = a1['dam']
                self.mm.setText(a2['name'])
                if a2['sire'] is not None:
                    a3 = a2['sire']
                    self.mmf.setText(a3['name'])
                if a2['dam'] is not None:
                    a3 = a2['dam']
                    self.mmm.setText(a3['name'])

    def input_connect(self):
        pass


class PropertyWindow(QtWidgets.QMainWindow):

    def __init__(self, main_screen, game):
        self.main = main_screen
        self.game = game
        super(PropertyWindow, self).__init__()
        uic.loadUi(os.path.join('ui_files', 'horse_property_screen.ui'), self)

        self.input_connect()

    def update(self, horse):
        data = to.get_rows('horse_properties', [horse]).iloc[0]
        due_date = to.query_to_dataframe(
            "SELECT due_date FROM horses WHERE horse_id = ?", [horse])['due_date'].values[0]

        msg = ''
        for prop, val in data.iteritems():
            msg += f'{prop}:  {val} \n'

        data = to.get_rows('horses', [horse]).iloc[0]
        for prop in ['leg_damage',  'ankle_damage', 'heart_damage']:
            msg += f'{prop}:  {data[prop]} \n'
        msg += f'Due Date: {due_date}\n'
        msg += f'Estimated Value: {of.horse_value(horse, self.game.day)}\n'


        self.property_box.setText(msg)

    def input_connect(self):
        pass


class NamingDialog(QtWidgets.QDialog):
    def __init__(self, main_screen, mother, gender):
        self.main = main_screen
        self.gender = gender
        super(NamingDialog, self).__init__()
        uic.loadUi(os.path.join('ui_files', 'naming_dialog.ui'), self)
        self.input_connect()
        self._random_name()
        if gender == 'M':
            word, pronoun = 'colt', 'him'
        else:
            word, pronoun = 'filly', 'her'
        msg = f"{mother} has given birth to a {word} what do you want to name {pronoun}?"
        self.message_display.setText(msg)

    def update(self, race_info):
        self._refresh_horse_list()
        self.horses_needed = race_info['horses_per_owner']
        msg_text = f'Track Length: {race_info["length"]} m'
        msg_text += '\nPurse Distribution'
        for i, p in enumerate(race_info['purse']):
            msg_text += f'\n\t{text.ordinal(i+1)} place: ${p:.2f}'
        self.race_info.setText(msg_text)
        self._update_number_needed()

    def input_connect(self):
        self.randomize.clicked.connect(self._random_name)
        self.accept.clicked.connect(self._use_name)

    def _random_name(self):
        """Generate a random name."""
        if self.gender == 'M':
            name = np.random.choice(hf.MALE_NAMES, 1)[0]
        else:
            name = np.random.choice(hf.FEMALE_NAMES, 1)[0]
        self.name_entry.setText(name)

    def _use_name(self):
        return self.close()


class BuildingBox(QMdiSubWindow):
    ROW_SPACING = 40  # Offset of each row

    def __init__(self, main_screen, game):
        self.main = main_screen
        self.game = game
        super(BuildingBox, self).__init__()
        uic.loadUi(os.path.join('ui_files', 'building_box.ui'), self)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        self._create_layout()
        self.input_connect()
        self.hide()

    def _create_layout(self):
        """Create the layout of information and buttons to allow for buying/selling
        buildings."""
        stable_pos = self.ROW_SPACING
        house_pos = self.ROW_SPACING
        misc_pos = self.ROW_SPACING
        for name, info in BUILDINGS.items():
            if info.get('type') == 'stable':
                row = BuildingRow(self.stable_tab, info, name, self.main)
                row.move(0, stable_pos)
                stable_pos += self.ROW_SPACING
            elif info.get('type') == 'housing':
                row = BuildingRow(self.house_tab, info, name, self.main)
                row.move(0, house_pos)
                house_pos += self.ROW_SPACING
            else:
                row = BuildingRow(self.misc_tab, info, name, self.main)
                row.move(0, misc_pos)
                misc_pos += self.ROW_SPACING
        self.land_price.setText(f'${LAND_COST}/Ha')

    def update(self):
        tab = self.disp_tab.currentWidget()
        if tab.objectName() == 'land_tab':
            self._update_land_tab()
        else:
            for row in tab.children():
                row.update()

    def input_connect(self):
        self.disp_tab.currentChanged.connect(self.update)
        self.buy_land_button.clicked.connect(self._buy_land)
        self.sell_land_button.clicked.connect(self._sell_land)
        self.hectare_input.valueChanged.connect(self._update_land_tab)

    def _buy_land(self):
        try:
            estate.buy_land(self.game.owner, self.hectare_input.value())
            self.main.update_money()
            self._update_land_tab()
        except estate.InsufficientFunds:
            self.main.display_message("You don't have enough money for that purchase.")

    def _sell_land(self):
        try:
            estate.sell_land(self.game.owner, self.hectare_input.value())
            self.main.update_money()
            self._update_land_tab()
        except estate.NotEnoughLand:
            self.main.display_message("You don't have that much free land.")

    def _update_land_tab(self):
        self.free_land.setText(f'{estate.free_land(self.game.owner)} Ha')
        if estate.free_land(self.game.owner) < self.hectare_input.value():
            self.sell_land_button.setEnabled(False)
        else:
            self.sell_land_button.setEnabled(True)

        if of.money(self.game.owner) < self.hectare_input.value()*LAND_COST:
            self.buy_land_button.setEnabled(False)
        else:
            self.buy_land_button.setEnabled(True)


class BuildingRow(QWidget):

    def __init__(self, parent_widget, info, building_name, main_screen):
        super(BuildingRow, self).__init__(parent_widget)
        self.info = info
        self.building = building_name
        self.main = main_screen
        self._create_widgets()
        self.input_connect()
        self.update()
        self.show()

    def _create_widgets(self):
        label = QLabel(self, text=self.info['name'].title())
        label.move(10, 4)
        self.amount = QLabel(self, text='0')
        self.amount.move(100, 4)
        self.buy_button = QPushButton(self, text=f'Buy (${self.info["cost"]})')
        self.buy_button.move(150, 0)
        self.sell_button = QPushButton(self, text=f'Sell')
        self.sell_button.move(250, 0)

    def input_connect(self):
        self.buy_button.clicked.connect(self.buy)
        self.sell_button.clicked.connect(self.sell)

    def buy(self):
        """Try to buy one of the building."""
        try:
            estate.add_building(self.main.game.owner, self.building)
        except estate.InsufficientFunds:
            self.main.display_message('You do not have enough money to buy that.')
        except estate.NotEnoughLand:
            self.main.display_message('Your estate is not large enough for that building.')
        self.parentWidget().parentWidget().parentWidget().parentWidget().update()

    def sell(self):
        """Try to sell one of the building."""
        try:
            estate.remove_building(self.main.game.owner, self.building)
        except ValueError:
            pass
        self.update()

    def update(self):
        number = estate.building_count(self.main.game.owner, self.building)
        self.amount.setText(f'{str(number)}       ')
        if number == 0:
            self.sell_button.setEnabled(False)
        else:
            self.sell_button.setEnabled(True)
        if of.money(self.main.game.owner) < self.info['cost']:
            self.buy_button.setEnabled(False)
        else:
            self.buy_button.setEnabled(True)

        self.main.update_money()


class EmployeeBox(QMdiSubWindow):
    hired = QtCore.pyqtSignal(int)
    fired = QtCore.pyqtSignal(int)

    def __init__(self, main_screen, game):
        self.main = main_screen
        self.game = game
        super(EmployeeBox, self).__init__()
        uic.loadUi(os.path.join('ui_files', 'employee_box.ui'), self)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        self._create_layout()
        self.update()
        self.input_connect()
        self.hide()

    def _create_layout(self):
        """Create the layout of information and buttons to allow for buying/selling
        buildings."""
        for employee_type, employee_info in EMPLOYEES.items():
            title = employee_info.get('plural_name', employee_info['name'] + 's')
            title = title.capitalize()
            tab = QWidget()
            tab.employee_type = employee_type
            self.tabWidget.addTab(tab, title)

            tab.setLayout(QtWidgets.QHBoxLayout())

            hire_scroll = QScrollArea()
            hire_scroll.setWidgetResizable(True)
            hire_scroll.setMinimumWidth(200)
            tab.layout().addWidget(hire_scroll)
            hire_inner = QFrame()
            hire_inner.setLayout(QtWidgets.QVBoxLayout())
            hire_scroll.setWidget(hire_inner)

            fire_scroll = QScrollArea()
            fire_scroll.setWidgetResizable(True)
            fire_scroll.setMinimumWidth(200)
            tab.layout().addWidget(fire_scroll)
            fire_inner = QFrame()
            fire_inner.setLayout(QtWidgets.QVBoxLayout())
            fire_scroll.setWidget(fire_inner)

    def update(self):
        # Update number stats
        self.current_salary.setText(f'Current Salary: ${ef.total_salary(self.game.owner)}/week')
        self.rooms_available.setText(f'Rooms Available: {estate.rooms_available(self.game.owner)}')

        # Update employee tiles
        tab = self.tabWidget.currentWidget()
        employees = to.query_to_dataframe("SELECT * FROM employees WHERE employer = 1 AND employee_type = ?", [tab.employee_type])
        hire = tab.children()[1].children()[0].children()[0]
        fire = tab.children()[2].children()[0].children()[0]
        self._clear_widget(hire, EmployeeTile)
        self._clear_widget(fire, EmployeeTile)
        for r, employee in employees.iterrows():
            tile = EmployeeTile(employee, tab, self.main, self, for_hire=True)
            hire.layout().addWidget(tile)

        employees = to.query_to_dataframe(
            "SELECT * FROM employees WHERE employer = ? AND employee_type = ?", [self.game.owner, tab.employee_type])
        for r, employee in employees.iterrows():
            tile = EmployeeTile(employee, tab, self.main, self, for_hire=False)
            fire.layout().addWidget(tile)

    def _clear_widget(self, widget, clear_type=None):
        """
        Delete all children of the specified type in the widget.
        Args:
            widget (PyQt5.QWidget): Delete the children of this widget.
            clear_type (class, None): Only delete children of this class. If None, will
                delete all children.

        Returns:
            None.
        """
        for c in widget.children():
            if clear_type is None:
                c.setParent(None)
            elif isinstance(c, clear_type):
                c.setParent(None)

    def input_connect(self):
        self.tabWidget.currentChanged.connect(self.update)
        self.hired.connect(self._hire_employee)
        self.fired.connect(self._fire_employee)

    def _hire_employee(self, employee_id):
        if estate.rooms_available(self.game.owner) <= 0:
            self.main.display_message(f"You don't have enough bedrooms to hire another employee.")
        else:
            self.main.display_message(f'You have hired [employees:{employee_id}]')
            ef.hire_employee(employee_id, self.game.owner)
            self.update()

    def _fire_employee(self, employee_id):
        self.main.display_message(f'You have fired [employees:{employee_id}]')
        ef.fire_employee(employee_id)
        self.update()


class EmployeeTile(QFrame):

    def __init__(self, info, tab, main_screen, employee_box, for_hire=True):
        super(EmployeeTile, self).__init__(tab)
        self.setStyleSheet(
            "EmployeeTile {background-color: rgb(175,175,245); margin:5px; border:1px solid rgb(0, 0, 0); }")
        self.info = info
        self.main = main_screen
        self.employee_box = employee_box
        self.for_hire = for_hire
        self._create_widgets()
        self.show()
        self.mouseDoubleClickEvent = self.hire_or_fire

    def _create_widgets(self):
        self.setLayout(QtWidgets.QVBoxLayout())
        label = QLabel(text=f"<b><center>{self.info['name']}</center></b>")
        self.layout().addWidget(label)
        label = QLabel(text=f"Salary: ${self.info['salary']}/week")
        self.layout().addWidget(label)

        # Add bonus info
        for bonus, b_info in EMPLOYEES[self.info['employee_type']]['bonuses'].items():
            text = f"{b_info['name']}: {self.info[bonus]}"
            label = QLabel(text=text)
            self.layout().addWidget(label)

        self.setFixedSize(self.sizeHint())

    def hire_or_fire(self, _):
        """Hire or fire the employee who was clicked on."""
        if self.for_hire:
            self.employee_box.hired.emit(self.info['employee_id'])
        else:
            self.employee_box.fired.emit(self.info['employee_id'])


def convert_to_links(msg):
    """Convert a string containing link indicators so that it contains proper links.

    To indicate a link in a string, use the form [TABLE_NAME:ID]. e.g. [horses:21] to
    indicate a link to the horse with the ID 21.
    """
    pattern = '\[[^\]]*]'
    links = re.findall(pattern, msg)
    normal_text = re.split(pattern, msg)
    output = ''
    for i, link in enumerate(links):
        info = link.strip('[]').split(':')
        output += normal_text[i]
        output += format_link(info[0], int(info[1]))
    output += normal_text[-1]
    return output


def format_link(table, id_, name=None):
    """Create a string to use as a link in the GUI.

    Args:
        table (str): The type of thing to link to (horses, owners, etc.)
        id_ (str or int): ID of the thing to link to.
        name (str or None): Name to use as the hyperlink code. If None, will use the
            name as stored in the database. If there is no column 'name', will
            default to the id.
    Returns:
          str
    """
    if name is None:
        info = to.get_rows(table, id_).iloc[0]
        try:
            name = info['name']
        except KeyError:
            name = id_
    return f"<a href=\"#{table}#{id_}\">{name}</a>"


MainScreen()
