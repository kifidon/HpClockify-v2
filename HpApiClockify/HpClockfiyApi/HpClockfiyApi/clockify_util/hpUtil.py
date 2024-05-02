import logging
import asyncio
from json import dumps, dump, loads
import pytz
import pyodbc
from datetime import datetime, timedelta, timezone

def getCurrentPaycycle():
    # Get the current date
    current_date = datetime.now()

    # Calculate the most recent Sunday (start of this week)
    start_of_this_week = current_date - timedelta(days=current_date.weekday() + 1)
    # Adjust if the start of the week falls on a Sunday
    if start_of_this_week.weekday() != 6:
        start_of_this_week += timedelta(days=-7)

    # Calculate the Sunday two weeks ago
    start_of_two_weeks_ago = start_of_this_week - timedelta(weeks=1)

    # Calculate the upcoming Saturday (end of this week)
    end_of_this_week = start_of_this_week + timedelta(days=6)

    # Format dates as strings in 'YYYY-MM-DD' format
    start_of_two_weeks_ago_formatted = start_of_two_weeks_ago.strftime('%Y-%m-%d')
    end_of_this_week_formatted = end_of_this_week.strftime('%Y-%m-%d')

    return start_of_two_weeks_ago_formatted, end_of_this_week_formatted


def getMonthYear():
    # Get the current date
    current_date = datetime.now()

    # Extract the month and year
    month = str(current_date.month)
    year = str(current_date.year)[2:]
    return month, year

def getAbbreviation(month = None, year = None ):
    months = {
        '01': 'Jan',
        '02': 'Feb',
        '03': 'Mar',
        '04': 'Apr',
        '05': 'May',
        '06': 'Jun',
        '07': 'Jul',
        '08': 'Aug',
        '09': 'Sep',
        '10': 'Oct',
        '11': 'Nov',
        '12': 'Dec'
    }
    if month is None:
        month, year = getMonthYear()
    return f"{ months.get(month, 'Invalid Month')} 20{year}"


def get_current_time():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def timeZoneConvert(dateTime, format='%Y-%m-%dT%H:%M:%SZ'):
    utcTimezone = pytz.utc
    localTimeZone = pytz.timezone('America/Denver')
    if isinstance(dateTime, str):
        dateTime = datetime.strptime(dateTime, format)
    output = utcTimezone.localize(dateTime).astimezone(localTimeZone)
    return  output.replace(tzinfo=None)

def timeDuration(duration_str):
    """
    Converts a duration string to hours.

    Args:
        duration_str (str): ISO 8601 duration format. In this format:
                "PT" indicates a period of time.
                "1H" indicates 1 hour.
                "30M" indicates 30 minutes.
            So, "PT1H30M" represents a duration of 1 hour and 30 minutes.

    Returns:
        float: Total duration in hours.
    """
    duration_str = duration_str[2:]
    hours, minutes = 0, 0
    if 'H' in duration_str:
        hours, duration_str = duration_str.split('H')
        hours = int(hours)
    if 'M' in duration_str:
        minutes = int( (duration_str.split('M'))[0] )
    total_minutes = hours * 60 + minutes

    # Round to the nearest 15 minutes
    rounded_minutes = round(total_minutes / 15) * 15
    # Convert rounded minutes back to hours
    rounded_hours = rounded_minutes / 60
    return rounded_hours

def is_within(date_string, window):
    """
    Checks if the given date string is within the specified window of days from the current date.

    Args:
        date_string (str): A string representing the date in the format '%Y-%m-%dT%H:%M:%SZ'.
        window (int): The number of days to consider for the window.

    Returns:
        bool: True if the date is within the window, False otherwise.
    """
    # Convert the date string to a datetime object
    date_object = datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)

    # Get the current date
    current_date = datetime.now(timezone.utc)

    # Calculate the difference between the two dates
    difference = current_date - date_object

    # Check if the difference is less than or equal to 7 days
    return difference <= timedelta(days=window)

def sqlConnect():
    """
    Connects to a SQL Server database.

    Returns:
        tuple: A tuple containing a cursor object and a connection object if the connection is successful, otherwise dict().
    """
    try:
        #server info 
        server = 'hpcs.database.windows.net'
        database = 'hpdb'
        username = 'hpUser'
        password = '0153HP!!'
        driver = '{ODBC Driver 18 for SQL Server}'
        # Establish the connection
        conn_str = f'DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;'
        conn = pyodbc.connect(conn_str)
        # Create a cursor object to interact with the database
        cursor = conn.cursor()
        return cursor, conn
    except pyodbc.Error as e:
        print(f"Error: {e}")
        return None ,None

def cleanUp(conn, cursor):
    """
    Closes the cursor and connection objects.

    Args:
        conn: The connection object to be closed.
        cursor: The cursor object to be closed.

    Returns:
        int: 1 if the cleanup is successful, 0 otherwise.
    """
    try: 
        cursor.close()
        conn.close()
        return "Completed"
    except pyodbc.Error as e:
        print(f"Error: {str(e)}")
        return "Bad Clean UP"
    