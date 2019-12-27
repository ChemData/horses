import sys
import os
import re
import numpy as np
from PyQt5 import QtWidgets, uic, QtCore
from PyQt5.QtWidgets import QApplication, QMessageBox, QMdiSubWindow, QMdiArea
from PyQt5.QtGui import QFont
from game_loop import Game
import table_operations as to
import owner_functions as of
import horse_functions as hf
import text_operations as text


class MainScreen(QtWidgets.QMainWindow):

    def __init__(self):
        self.app = QApplication(sys.argv)
        super(MainScreen, self).__init__()
        uic.loadUi(os.path.join('ui_files', 'main_screen.ui'), self)

        self.game = Game('20110101', self)

        self._setup_sub_windows()

        self.input_connect()
        self.show()
        self.start_game()

        sys.exit(self.app.exec())

    def _setup_sub_windows(self):
        self.race_window = RaceWindow(self, self.game)

        self.pedigree_window = PedigreeWindow(self, self.game)

        self.breeding_window = BreedingBox(self, self.game)
        self.mdi.addSubWindow(self.breeding_window)

        self.trading_window = TradeBox(self, self.game)
        self.mdi.addSubWindow(self.trading_window)

    def start_game(self):
        self.game.simulate_horse_population(50)
        self.game.automated = True

    def input_connect(self):
        self.next_day.clicked.connect(self._next_day_push)
        self.next_n_days.clicked.connect(self._next_n_days_push)
        self.day_amount_entry.valueChanged.connect(self._change_n_days_text)
        self.message_box.anchorClicked.connect(self.display_link_info)
        self.entity_info_box.anchorClicked.connect(self.display_link_info)
        self.actionBreeding.triggered.connect(self._show_breeding_window)
        self.actionTrading.triggered.connect(self._show_trading_window)
        self.actionPedigree.triggered.connect(self._show_pedigree_window)

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

    def _show_breeding_window(self):
        self.trading_window.hide()
        self.breeding_window.show()
        self.breeding_window.update()

    def _show_trading_window(self):
        self.breeding_window.hide()
        self.trading_window.show()
        #self.trading_window.setGeometry(20, 0, 500, 500)
        self.trading_window.update()

    def _show_pedigree_window(self):
        self.pedigree_window.show()

    def display_link_info(self, url):
        """Display information about the thing that was just clicked on. Also show
        information in the pedigree window if it is open."""
        _, entity_type, id_ = url.toString().split('#')
        id_ = int(id_)
        if entity_type == 'horses':
            info = self.game.horse_info(id_)
            if self.pedigree_window.isVisible():
                self.pedigree_window.update(id_)
        else:
            info = ''
        info = convert_to_links(info)
        self.entity_info_box.setText(info)

    def display_message(self, msg):
        """Display an update in the main window."""
        msg = convert_to_links(msg)
        self.message_box.setText(msg)

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

    def show_list_horse_info(self, t):
        """Display the information of a horse in the list."""
        info = self.game.horse_info(t.horse_id)
        info = convert_to_links(info)
        self.entity_info_box.setText(info)


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
        horses = self.main.game.breedable_horses()
        self.dam_selection.clear()
        for i, dam in horses[horses['gender'] == 'F'].iterrows():
            item = QtWidgets.QListWidgetItem()
            item.horse_id = dam['id']
            item.setData(0, f"{dam['name']}")
            self.dam_selection.insertItem(1, item)

        self.sire_selection.clear()
        for i, sire in horses[horses['gender'] == 'M'].iterrows():
            item = QtWidgets.QListWidgetItem()
            item.horse_id = sire['id']
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
        for h in self.game.living_horses(self.game.owner):
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
        self.counterparty = None

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
        if self.sell_radio.isChecked():
            owner_id = self.game.owner
            self.horse_selection_label.setText('Your Horses')
        else:
            owner_id = self.counterparty_selection.currentData()
            self.horse_selection_label.setText('Their Horses')
        horse_ids = self.main.game.living_horses(owner_id)
        self.horse_selection.clear()
        for horse in horse_ids:
            name = to.get_column('horses', 'name', horse).iloc[0]['name']
            item = QtWidgets.QListWidgetItem()
            item.horse_id = horse
            item.setData(0, name)
            self.horse_selection.insertItem(1, item)

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

        if buying and price > of.money(self.game.owner):
            self.main.display_message("You don't have that much money and debt hasn't been implemented.")
            return

        counterparty = self.counterparty_selection.currentData()
        decision = of.evaluate_trade(counterparty, horse, price, not buying)
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
            if row['id'] != self.game.owner and row['id'] != 1:
                item = QtWidgets.QListWidgetItem()
                item.owner_id = row['id']
                item.setData(0, row['name'])
                self.counterparty_selection.blockSignals(True)
                self.counterparty_selection.addItem(row['name'], userData=row['id'])
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
