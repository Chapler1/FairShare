import sys
from PyQt5.QtWidgets import (
    QStackedLayout, QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QScrollArea, QFrame, QCheckBox, QInputDialog, QComboBox
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QIcon, QFontDatabase
import datetime
import sqlite3
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.font_manager

global font_regular, font_bold

class Person:
    def __init__(self, name, val=0):
        self.name = name
        self.val = val

def add_fonts():
    font_regular = None
    font_bold = None

    # regular font
    fontId = QFontDatabase.addApplicationFont("assets/montserrat_regular.ttf")
    if fontId != -1:
        fontFamilies = QFontDatabase.applicationFontFamilies(fontId)
        font_regular = QFont(fontFamilies[0], 18)
   
    # bold font
    fontId = QFontDatabase.addApplicationFont("assets/montserrat_bold.ttf")
    if fontId != -1:
        fontFamilies = QFontDatabase.applicationFontFamilies(fontId)
        font_bold = QFont(fontFamilies[0], 18)

    return font_regular, font_bold

def calculate_bills(persons, show_individuals):
    print("entering calculate_bills")
    total = sum(p.val for p in persons)
    per_person = total / len(persons) if persons else 0
    results = []

    # Calculate initial debts or credits for each person
    debts = [[p, per_person - p.val] for p in persons]
    final_balances = {p.name: per_person - p.val for p in persons}  # Track final balances

    # Separate out debtors and creditors
    debtors = [[p.name, amount] for p, amount in debts if amount > 0]
    creditors = [[p.name, amount] for p, amount in debts if amount < 0]

    # Processing payments from debtors to creditors
    for debtor in debtors:
        debtor_name, debtor_amount = debtor

        while debtor_amount > 0:
            for creditor in creditors:
                creditor_name, creditor_amount = creditor

                if creditor_amount >= 0:
                    continue  # Skip if this creditor has no more to be reimbursed

                pay_amount = min(debtor_amount, -creditor_amount)
                debtor_amount -= pay_amount
                creditor[1] += pay_amount  # Update the creditor's remaining credit

                # Update final balances for debtor and creditor
                final_balances[debtor_name] -= pay_amount
                final_balances[creditor_name] += pay_amount

                # Formatting the transaction with HTML for green and bold "pays" and bold amount
                transaction = f"{debtor_name} <b><span style='color: green;'>pays</span></b> {creditor_name} <b>${pay_amount:.2f}</b>"
                results.append(transaction)

                if debtor_amount <= 0:
                    break

    # If show_individuals is True, add individual's final balances
    if show_individuals:
        for name, balance in final_balances.items():
            adjusted_balance = per_person - balance  # This is the final amount they need to settle up
            if adjusted_balance > 0:
                results.append(f"{name} is actually paying: <b>${adjusted_balance:.2f}</b>")
            else:
                results.append(f"{name} is owed: <b>${-adjusted_balance:.2f}</b>")

    print("leaving on_calculate")
    return "\n".join(results)

class BillCalculator(QWidget):
    def __init__(self):
        super().__init__()
        self.persons = []  # Initialize an empty list of persons
        self.person_entries = []  # Initialize an empty list for person entry widgets
        self.show_individuals = False  # Default value
        self.init_database()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Bill's Bill Calculator")
        self.setStyleSheet("background-color: #391053")
        self.font_regular, self.font_bold = add_fonts()

        main_layout = QVBoxLayout(self)
        # Calculate previous month and current year for title
        # Calculate previous month and current year for title
        current_date = datetime.datetime.now()
        first_day_of_current_month = current_date.replace(day=1)
        last_day_of_previous_month = first_day_of_current_month - datetime.timedelta(days=1)
        self.previous_month_year = last_day_of_previous_month.strftime("%m/%Y")  # Changed to MM/YYYY


        # Create a stacked layout to switch between main page and settings
        self.stacked_layout = QStackedLayout()

        # First page (Main UI)
        self.main_page = QWidget()
        self.setupMainPage()  # Set up the main page UI
        self.stacked_layout.addWidget(self.main_page)

        self.graph_page = GraphPage(self)
        
        self.stacked_layout.addWidget(self.graph_page)

        # Second page (Settings UI)
        self.settings_page = SettingsPage(self)
        self.stacked_layout.addWidget(self.settings_page)

        # Add the stacked layout to the main layout
        main_layout.addLayout(self.stacked_layout)

        # Bottom Layout for back and settings buttons
        bottom_layout = QHBoxLayout()

        # Back button
        back_button = QPushButton()  # No text needed, as we're using an icon
        back_button.setIcon(QIcon('assets/back_icon.png'))
        back_button.setIconSize(QSize(36, 36))
        back_button.setStyleSheet("QPushButton { border: none; background-color: transparent; }")
        back_button.clicked.connect(self.show_main_page)  # Connect to show_main_page method
        bottom_layout.addWidget(back_button)

        bottom_layout.addStretch()  # Pushes the settings button to the right

        # Dropdown for load configurations
        self.load_dropdown = QComboBox()
        self.load_dropdown.setMinimumWidth(200)
        self.load_dropdown.setMaximumWidth(200)
        self.load_dropdown.setFont(self.font_regular)
        self.load_dropdown.setStyleSheet("QComboBox { color: white; background-color: #5a2675; border: 1px solid white; }")
        self.update_dropdown()  # Populate the dropdown

        # Load button next to dropdown
        load_button = QPushButton("Load")
        load_button.setFont(self.font_regular)
        load_button.setStyleSheet("QPushButton { color: white; background-color: #5a2675; border: 1px solid white; padding: 6px}")
        load_button.clicked.connect(self.load_settings)

        bottom_layout.addWidget(self.load_dropdown)
        bottom_layout.addWidget(load_button)

        # Save button
        save_button = QPushButton("Save")
        save_button.setFont(self.font_regular)
        save_button.setStyleSheet("QPushButton { color: white; background-color: #5a2675; border: 1px solid white; padding: 6px}")
        save_button.clicked.connect(self.save_settings)  # Connect to a function to save settings
        bottom_layout.addWidget(save_button)

        # Add Delete button
        delete_button = QPushButton("Delete")
        delete_button.setFont(self.font_regular)
        delete_button.setStyleSheet("QPushButton { color: white; background-color: #5a2675; border: 1px solid white; padding: 6px}")
        delete_button.clicked.connect(self.delete_config)
        bottom_layout.addWidget(delete_button)

        bottom_layout.addStretch()

        # Graph button
        graph_button = QPushButton()  # No text needed, as we're using an icon
        graph_button.setIcon(QIcon('assets/graph_icon.png'))
        graph_button.setIconSize(QSize(48, 48))  # Adjust size as needed
        graph_button.setStyleSheet("QPushButton { border: none; background-color: transparent; }")
        graph_button.clicked.connect(self.show_graph)  # Connect to a method to show graph
        bottom_layout.addWidget(graph_button)

        # Settings button
        settings_button = QPushButton()  # No text needed, as we're using an icon
        settings_button.setIcon(QIcon('assets/settings_icon.png'))
        settings_button.setIconSize(QSize(48, 48))
        settings_button.setStyleSheet("QPushButton { border: none; background-color: transparent; }")
        settings_button.clicked.connect(self.show_settings)  # Connect to the show_settings method
        bottom_layout.addWidget(settings_button)

        # Add the bottom layout to the main layout
        main_layout.addLayout(bottom_layout)

        self.setLayout(main_layout)
        self.resize(400, 800)
    
    def init_database(self):
        self.conn = sqlite3.connect('configurations.db')
        self.c = self.conn.cursor()
        # Uncomment the next 2 lines to reset the table
        # self.c.execute('DROP TABLE IF EXISTS configurations')
        # self.c.execute('DROP TABLE IF EXISTS bill_history')

        self.c.execute('''CREATE TABLE IF NOT EXISTS configurations (
                        config_id INTEGER PRIMARY KEY,
                        config_name TEXT UNIQUE,
                        person_names TEXT,
                        show_individuals BOOLEAN)''')
        
        self.c.execute('''CREATE TABLE IF NOT EXISTS bill_history (
                        bill_id INTEGER PRIMARY KEY,
                        config_id INTEGER,
                        total_bill REAL,
                        bill_month TEXT,
                        FOREIGN KEY (config_id) REFERENCES configurations(config_id))''')
        
        self.conn.commit()

    def updateShowIndividuals(self, show):
        self.show_individuals = show

    def delete_config(self):
        config_name = self.load_dropdown.currentText()  # Get the currently selected configuration name
        if config_name:  # Ensure there is a configuration selected to delete
            # Execute the delete operation
            self.c.execute("DELETE FROM configurations WHERE config_name=?", (config_name,))
            self.conn.commit()  # Commit the changes to the database
            self.update_dropdown()  # Refresh the dropdown list to reflect the deletion
            # Optional: Notify the user or update the UI to reflect the deletion
        else:
            print("No configuration selected to delete")  # Handle the case of no selection or error

    def show_graph(self):
        config_name = self.load_dropdown.currentText()
        if config_name:  # Ensure there is a selected configuration
            self.graph_page.update_graph(config_name)
            self.stacked_layout.setCurrentWidget(self.graph_page)
        else:
            print("No configuration selected to show graph")  # Handle case where there is no configuration selected

    def fetch_monthly_data(self, config_name):
        # Fetch monthly data for the given config_name from the database
        # Update this query to join configurations with bill_history
        query = """
        SELECT bh.total_bill, strftime('%m/%Y', bh.bill_month) as formatted_month
        FROM bill_history bh
        JOIN configurations c ON c.config_id = bh.config_id
        WHERE c.config_name=? 
        ORDER BY bh.bill_month
        """
        self.c.execute(query, (config_name,))
        rows = self.c.fetchall()

        # Convert rows into a list of dictionaries
        data = [{'month': row[1], 'total_bill': row[0]} for row in rows]
        return data



    def show_settings(self):
        # Switch to the settings page
        self.stacked_layout.setCurrentWidget(self.settings_page)

    def load_settings(self):
        config_name = self.load_dropdown.currentText()
        self.c.execute("SELECT config_id, person_names FROM configurations WHERE config_name=?", (config_name,))
        row = self.c.fetchone()

        if row:
            config_id, person_names = row
            self.persons = [Person(name) for name in person_names.split(',')]
            self.updatePersonEntries()

    def update_dropdown(self):
        # Populate or refresh the dropdown menu with available configurations
        self.load_dropdown.clear()
        for row in self.c.execute('SELECT config_name FROM configurations'):
            self.load_dropdown.addItem(row[0])

    def save_settings(self):
        # Define the style for the QInputDialog
        inputDialogStyle = """
        QWidget {
            color: #FFFFFF;
            background-color: #391053;
            font: 18pt self.font_regular;
        }
        QLineEdit {
            border: 1px solid white;
            background-color: #5a2675;
            color: white;
        }
        QPushButton {
            color: white;
            background-color: #5a2675;
            border: 1px solid white;
            padding: 6px;
            font: 18pt self.font_regular;
        }
        """

        # Create an instance of QInputDialog and set its style
        inputDialog = QInputDialog(self)
        inputDialog.setStyleSheet(inputDialogStyle)

        # Configure and display the dialog
        inputDialog.setInputMode(QInputDialog.TextInput)
        inputDialog.setWindowTitle("Save Configuration")
        inputDialog.setLabelText("Configuration Name:")
        inputDialog.setTextValue("")
        inputDialog.resize(400, 200)  # This might not affect some platforms

        okPressed = inputDialog.exec_()
        config_name = inputDialog.textValue()

        if okPressed and config_name:
            # Calculate the total bill
            total_bill = sum(p.val for p in self.persons)
            # Get the current month in YYYY-MM format
            current_month = datetime.datetime.now().strftime("%Y-%m")
            persons_str = ','.join([person.name for person in self.persons])

            # Insert or update configuration
            self.c.execute("INSERT OR REPLACE INTO configurations (config_id, config_name, person_names, show_individuals) VALUES ((SELECT config_id FROM configurations WHERE config_name = ?), ?, ?, ?)", (config_name, config_name, ','.join([p.name for p in self.persons]), self.show_individuals))
            config_id = self.c.lastrowid

            self.conn.commit()
            self.update_dropdown()
        else:
            # Handle the case where the user did not enter a name or pressed cancel
            print("Save cancelled or no name entered.")

    def setupMainPage(self):
        self.main_layout = QVBoxLayout(self.main_page)

        # Title Label
        title_label = QLabel(f'Utility Bill For {self.previous_month_year}')
        title_label.setFont(self.font_bold)
        title_label.setStyleSheet("color: #ffffff;")  # Set text color to white
        title_label.setAlignment(Qt.AlignCenter)  # Align the text to the center
        self.main_layout.addWidget(title_label)
        
        # Dynamic Utility Entries Area
        self.person_entries_layout = QVBoxLayout()
        self.main_layout.addLayout(self.person_entries_layout)

        # Calculate Button - Initialized once and always visible
        self.calculate_button = QPushButton('Calculate')
        self.calculate_button.setStyleSheet("background-color: #c9a8f1; color: white;")
        self.calculate_button.setFont(self.font_regular)
        self.calculate_button.clicked.connect(self.on_calculate)
        self.main_layout.addWidget(self.calculate_button)

        # Total Bill Label - Initialized once and always visible
        self.total_bill_label = QLabel('')
        self.total_bill_label.setStyleSheet("color: #ffffff;")
        self.total_bill_label.setFont(self.font_regular)
        self.total_bill_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.total_bill_label)

        # Results Area - Initialized once and always visible
        self.scroll_area = QScrollArea(self.main_page)
        self.scroll_area.setWidgetResizable(True)
        self.main_layout.addWidget(self.scroll_area)
        self.result_frame = QFrame()
        self.result_frame.setStyleSheet("background-color: #5a2675;")
        self.result_layout = QVBoxLayout()
        self.result_frame.setLayout(self.result_layout)
        self.scroll_area.setWidget(self.result_frame)

        self.updatePersonEntries()  # Populate with initial or empty person entries

    def updatePersonEntries(self):
        # Clear existing person entries from layout
        while self.person_entries_layout.count():
            item = self.person_entries_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Now, self.person_entries_layout is empty, ready to add new widgets
        for person in self.persons:
            # Create and style the label
            label = QLabel(f"{person.name}'s payment:")
            label.setStyleSheet("color: white;")  # Apply white color to text
            label.setFont(self.font_regular)  # Apply common font

            # Create and style the entry box
            payment_entry = QLineEdit()
            payment_entry.setObjectName(f"entry_for_{person.name}")  # Set unique object name
            payment_entry.setFont(self.font_regular)  # Apply common font
            payment_entry.setStyleSheet("color: white; background-color: #5a2675;")  # Set text color to white and background to a darker shade

            # Create a container widget to hold the label and entry side by side
            container_widget = QWidget()
            container_layout = QHBoxLayout(container_widget)  # Use this layout to arrange elements horizontally within the container
            container_layout.addWidget(label)
            container_layout.addWidget(payment_entry)
            container_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins if desired

            # Add the container widget to the person entries layout
            self.person_entries_layout.addWidget(container_widget)

    def on_calculate(self):
        print("entering on_calculate")
        try:
            total_bill = 0  # Initialize total bill

            # Reset all persons' values
            for person in self.persons:
                person.val = 0  # Default to 0 in case of invalid or no input

            # Update each person's payment from corresponding QLineEdit and calculate total bill
            for person in self.persons:
                payment_entry = self.findChild(QLineEdit, f"entry_for_{person.name}")
                if payment_entry and payment_entry.text():  # Ensure it's found and not empty
                    payment = float(payment_entry.text())
                    person.val = payment  # Convert text to float and assign to person.val
                    total_bill += payment  # Add to total bill

            # Display total bill
            self.total_bill_label.setText(f"Total Bill: ${total_bill:.2f}")

            # Ensure there is a selected configuration
            config_name = self.load_dropdown.currentText()
            if config_name:
                # Only call update function if total bill is greater than 0
                if total_bill > 0:
                    self.update_total_bill_in_database(total_bill, config_name)
                    
        except ValueError:
            self.total_bill_label.setText("Invalid input. Please enter numeric values.")
            return  # Return early if any conversion fails

        # Display total bill
        self.total_bill_label.setText(f"Total Bill: ${total_bill:.2f}")

        # Pass the show_individuals attribute to the calculate_bills function
        results = calculate_bills(self.persons, self.show_individuals)
        self.display_results(results.split('\n'))

        print("leaving on_calculate")

    def update_total_bill_in_database(self, total_bill, config_name):
        if config_name and total_bill > 0:  # Ensure there is a config selected and total bill is greater than 0
            # Fetch the configuration ID from the configurations table
            self.c.execute("SELECT config_id FROM configurations WHERE config_name=?", (config_name,))
            config_row = self.c.fetchone()
            
            if config_row:  # Ensure configuration is found
                config_id = config_row[0]
                
                # Check if an entry for this month and config_id already exists in bill_history
                self.c.execute("SELECT * FROM bill_history WHERE config_id=? AND bill_month=?", (config_id, self.previous_month_year))
                if self.c.fetchone():
                    # Update the existing entry in bill_history
                    self.c.execute("UPDATE bill_history SET total_bill=? WHERE config_id=? AND bill_month=?", (total_bill, config_id, self.previous_month_year))
                else:
                    # Insert a new entry into bill_history only if total_bill is greater than 0
                    self.c.execute("INSERT INTO bill_history (config_id, total_bill, bill_month) VALUES (?, ?, ?)", (config_id, total_bill, self.previous_month_year))
                self.conn.commit()
            else:
                print("No existing configuration found for this name. Please save this as a new configuration or choose an existing one.")
        else:
            # Handle the case where total_bill is 0 or no config_name is provided
            if total_bill == 0:
                print("No bill to update as total is $0.")
            if not config_name:
                print("No configuration name provided.")


    # In the BillCalculator class
    def insert_or_update_history(self, config_name, month, total_bill):
    # Fetch the configuration ID first
        self.c.execute("SELECT config_id FROM configurations WHERE config_name=?", (config_name,))
        config = self.c.fetchone()
        
        if config:
            config_id = config[0]
            # Check if an entry for this month and config_id already exists in bill_history
            self.c.execute("SELECT * FROM bill_history WHERE config_id=? AND bill_month=?", (config_id, month))
            if self.c.fetchone():
                # Entry exists, update it
                self.c.execute("UPDATE bill_history SET total_bill=? WHERE config_id=? AND bill_month=?", (total_bill, config_id, month))
            else:
                # Entry does not exist, insert a new record
                self.c.execute("INSERT INTO bill_history (config_id, total_bill, bill_month) VALUES (?, ?, ?)", (config_id, total_bill, month))
            self.conn.commit()
        else:
            print(f"Configuration with name '{config_name}' does not exist.")


    def display_results(self, results):
        for i in reversed(range(self.result_layout.count())):
            widget = self.result_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        for line in results:
            label = QLabel()
            label.setText(line)  # Set the text as HTML
            label.setStyleSheet("color: #ffffff; text-align: left;")
            label.setFont(self.font_regular)
            self.result_layout.addWidget(label)

    def show_main_page(self):
        # Switch to the main page
        self.stacked_layout.setCurrentWidget(self.main_page)

    def updatePersons(self, data, action):
        if action == 'add':
            self.persons.append(data)
        elif action == 'remove':
            self.persons = [p for p in self.persons if p.name != data]
        self.updatePersonEntries()  # Refresh the UI to reflect changes
        return self.persons  # returning the modified list might be helpful

    # Separate method to get person names for clarity and reuse
    def getPersonNames(self):
        return [p.name for p in self.persons]


class GraphPage(QWidget):
    def __init__(self, bill_calculator, parent=None):
        super().__init__(parent)
        self.bill_calculator = bill_calculator
        self.layout = QVBoxLayout(self)
        self.figure = plt.figure(facecolor='none')  # Set background as transparent
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setStyleSheet("background-color:transparent;")  # Ensure the canvas is transparent
        self.layout.addWidget(self.canvas)

    def update_graph(self, config_name):
        
        self.figure.clear()
        # Set the axes to be transparent and lines to be white
        ax = self.figure.add_subplot(111, facecolor='none')
        ax.spines['bottom'].set_color('white')
        ax.spines['top'].set_color('white')
        ax.spines['right'].set_color('white')
        ax.spines['left'].set_color('white')
        ax.tick_params(axis='x', colors='white')
        ax.tick_params(axis='y', colors='white')
        ax.xaxis.label.set_color('white')
        ax.yaxis.label.set_color('white')
        ax.title.set_color('white')

        # Add grid lines to make it easier to read
        ax.grid(color='gray', linestyle='-', linewidth=0.5, alpha=0.7)  # Customize as needed

        # Fetch data from the database
        data = self.bill_calculator.fetch_monthly_data(config_name)

        # Ensure data is sorted by the 'month' field, which requires converting the month strings to datetime objects
        if data:
            # Convert 'month' strings to datetime objects for sorting
            data = sorted(data, key=lambda x: datetime.datetime.strptime(x['month'], "%m/%Y"))

            # Extract the sorted data
            months = [d['month'] for d in data]
            total_bills = [d['total_bill'] for d in data]

            # Plotting the data with specified styles
            ax.plot(months, total_bills, marker='o', color='white', linewidth=2)  # Line is white and slightly thicker
            ax.set_title(f"Monthly Total Bill for {config_name}", 
                     fontdict={'fontname': 'MS Reference Sans Serif', 'size': 24, 'color': 'white'})
            ax.set_xlabel("Month", fontdict={'fontname': 'MS Reference Sans Serif', 'size': 20, 'color': 'white'})
            ax.set_ylabel("Total Bill ($)", fontdict={'fontname': 'MS Reference Sans Serif', 'size': 20, 'color': 'white'})

            # Rotate x-axis labels to prevent overlap
            plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor", color='white')

        else:
            ax.text(0.5, 0.5, 'No data available', horizontalalignment='center', verticalalignment='center', color='white')

        self.canvas.draw()


class SettingsPage(QWidget):
    def __init__(self, bill_calculator):
        super().__init__()
        self.bill_calculator = bill_calculator
        self.show_individuals = False  # Track the state of showing individuals
        self.initUI()

    def initUI(self):
        self.layout = QVBoxLayout(self)
        self.setLayout(self.layout)
        self.layout.setAlignment(Qt.AlignTop)
        self.font_regular, self.font_bold = add_fonts()

        lineEditStyle = "QLineEdit { color: white; border: 1px solid white; background-color: #5a2675; padding: 6px; }"
        comboBoxStyle = "QComboBox { color: white; border: 1px solid white; background-color: #5a2675; padding: 6px; combobox-popup: 0; }"
        buttonStyle = "QPushButton { color: white; border: 1px solid white; background-color: #5a2675; padding: 6px; }"

        # Settings Title
        title_label = QLabel("Settings")
        title_label.setFont(self.font_bold)
        title_label.setStyleSheet("color: #ffffff; text-align: center;")
        title_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(title_label)


        # Layout for adding a person
        addPersonLayout = QHBoxLayout()
        self.addPersonLineEdit = QLineEdit()
        self.addPersonLineEdit.setPlaceholderText("Enter Name to Add")
        self.addPersonLineEdit.setFont(self.font_regular)
        self.addPersonLineEdit.setStyleSheet(lineEditStyle)
        self.addPersonButton = QPushButton("Add Person")
        self.addPersonButton.setFont(self.font_regular)
        self.addPersonButton.setStyleSheet(buttonStyle)
        self.addPersonButton.clicked.connect(self.addPerson)
        addPersonLayout.addWidget(self.addPersonLineEdit)
        addPersonLayout.addWidget(self.addPersonButton)
        self.layout.addLayout(addPersonLayout)  # Adding the add person layout to the main layout

        # Layout for removing a person
        removePersonLayout = QHBoxLayout()
        self.removePersonComboBox = QComboBox()
        self.removePersonComboBox.setFont(self.font_regular)
        self.removePersonComboBox.setStyleSheet(comboBoxStyle)
        self.removePersonButton = QPushButton("Remove Person")
        self.removePersonButton.setFont(self.font_regular)
        self.removePersonButton.setStyleSheet(buttonStyle)
        self.removePersonButton.clicked.connect(self.removePerson)
        removePersonLayout.addWidget(self.removePersonComboBox)
        removePersonLayout.addWidget(self.removePersonButton)
        self.layout.addLayout(removePersonLayout)  # Adding the remove person layout to the main layout

        # Add Bill History Button
        self.addBillHistoryButton = QPushButton("Add Bill History")
        self.addBillHistoryButton.setFont(self.font_regular)
        self.addBillHistoryButton.setStyleSheet(buttonStyle)
        self.addBillHistoryButton.clicked.connect(self.addBillHistory)
        self.layout.addWidget(self.addBillHistoryButton)

        # Show/Hide Individual Values Button
        self.toggle_individuals_btn = QPushButton("Not Showing Individual Values")
        self.toggle_individuals_btn.setFont(self.font_regular)
        self.toggle_individuals_btn.setStyleSheet(buttonStyle)
        self.toggle_individuals_btn.clicked.connect(self.toggleShowIndividuals)
        self.layout.addWidget(self.toggle_individuals_btn)

        self.populatePersonComboBox()  # Initial population of the ComboBox

    # Method to populate the ComboBox with current persons
    def populatePersonComboBox(self):
        self.removePersonComboBox.clear()  # Clearing all current items
        self.removePersonComboBox.addItems(self.bill_calculator.getPersonNames())

    def addPerson(self):
        name = self.addPersonLineEdit.text()
        if name:
            person = Person(name)
            self.bill_calculator.updatePersons(person, 'add')
            self.addPersonLineEdit.clear()  # Clear the line edit
            self.populatePersonComboBox()  # Repopulate the ComboBox

    def removePerson(self):
        name = self.removePersonComboBox.currentText()
        if name:
            self.bill_calculator.updatePersons(name, 'remove')
            self.populatePersonComboBox()  # Repopulate the ComboBox after removing
    
    def toggleShowIndividuals(self):
        # Toggle the show_individuals state in the BillCalculator instance
        self.bill_calculator.show_individuals = not self.bill_calculator.show_individuals
        
        # Update the button text based on the new state
        btn_text = "Showing Individual Values" if self.bill_calculator.show_individuals else "Not Showing Individual Values"
        self.toggle_individuals_btn.setText(btn_text)

    # Within the SettingsPage class
    def addBillHistory(self):
        config_name = self.bill_calculator.load_dropdown.currentText()
        if not config_name:
            print("No configuration selected!")
            return

        # Define the style for the QInputDialog
        inputDialogStyle = """
        QWidget {
            color: #FFFFFF;
            background-color: #391053;
            font: 18pt 'Futura';
        }
        QLineEdit {
            border: 1px solid white;
            background-color: #5a2675;
            color: white;
        }
        QPushButton {
            color: white;
            background-color: #5a2675;
            border: 1px solid white;
            padding: 6px;
            font: 18pt self.font_bold;
        }
        """

        # Create an instance of QInputDialog and set its style for Month
        monthDialog = QInputDialog(self)
        monthDialog.setStyleSheet(inputDialogStyle)
        monthDialog.setInputMode(QInputDialog.TextInput)
        monthDialog.setWindowTitle("Add Bill History")
        monthDialog.setLabelText("Month:")
        monthDialog.setTextValue("")
        monthDialog.resize(400, 200)

        # Execute the month dialog
        okPressedMonth = monthDialog.exec_()
        month = monthDialog.textValue()

        # Repeat for the total bill
        billDialog = QInputDialog(self)
        billDialog.setStyleSheet(inputDialogStyle)
        billDialog.setInputMode(QInputDialog.DoubleInput)
        billDialog.setWindowTitle("Add Bill History")
        billDialog.setLabelText("Total Bill:")
        billDialog.setDoubleValue(0.0)
        billDialog.setDoubleRange(0.0, 10000.0)
        billDialog.resize(400, 200)

        # Execute the bill dialog
        okPressedBill = billDialog.exec_()
        total_bill = billDialog.doubleValue()

        if okPressedMonth and okPressedBill:
            # Now insert or update the data in the database
            self.bill_calculator.insert_or_update_history(config_name, month, total_bill)
        else:
            print("Operation cancelled or no data entered.")


def main():
    app = QApplication(sys.argv)
    ex = BillCalculator()
    ex.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()

    def display_results(self, results):
        # Clear previous results
        for i in reversed(range(self.result_layout.count())):
            widget = self.result_layout.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)

        # Display new results
        for line in results:
            label = QLabel(line)
            label.setStyleSheet("color: #ffffff; text-align: left;")
            label.setFont(self.font_regular)
            self.result_layout.addWidget(label)

    def show_main_page(self):
        # Switch to the main page
        self.stacked_layout.setCurrentWidget(self.main_page)

    def updatePersons(self, data, action):
        if action == 'add' and isinstance(data, Person):
            self.persons.append(data)
        elif action == 'remove':
            self.persons = [p for p in self.persons if p.name != data]
        self.updatePersonEntries()  # Refresh the UI to reflect changes
