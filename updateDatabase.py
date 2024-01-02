import sqlite3
from datetime import datetime

# Connect to the database
conn = sqlite3.connect('configurations.db')
c = conn.cursor()

# Fetch all records that need updating
c.execute("SELECT bill_id, bill_month FROM bill_history")
rows = c.fetchall()

# Update each record with the new date format
for row in rows:
    bill_id, old_date = row
    # Convert 'YYYY-MM' to 'MM/YYYY'
    new_date = datetime.strptime(old_date, "%Y-%m").strftime("%m/%Y")

    # Update the record
    c.execute("UPDATE bill_history SET bill_month = ? WHERE bill_id = ?", (new_date, bill_id))

# Commit changes and close the connection
conn.commit()
conn.close()
