from .. Loggers import setup_background_logger
import asyncio
from json import dumps, dump, loads, JSONDecodeError
import pytz
import pyodbc
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs
import ast

def reverseForOutput(data:dict):
    data_lines = dumps(data, indent=4).split('\n')
    reversed_data = '\n'.join(data_lines[::-1])
    return reversed_data

def check_category_for_deletion(category_id, categories):
    """
    Check if a category should be deleted based on its presence in the categories list.

    Args:
    category_id (str): The ID of the category to check.
    categories (list of dict): A list of category dictionaries.

    Returns:
    bool: True if the category should not be deleted (i.e., it is found in the list), False otherwise.
    """
    # Loop through each category in the list
    for category in categories:
        # Check if the current category's ID matches the given category ID
        if category['id'] == category_id:
            # If a match is found, return False (do not delete)
            return False
    # If no match is found after checking all categories, return True (delete)
    return True

def bytes_to_dict(byte_string):
    logger = setup_background_logger('DEBUG')
    try:

        # Decode the byte string into a regular string
        json_string = byte_string.decode('utf-8')

        # Parse the JSON string into a Python dictionary
        data = parse_qs(json_string)
        if data:
            for key, value in data.items():
                try:
                    data[key] = ast.literal_eval(value[0])
                except SyntaxError:
                    data[key] = value[0]
            print(data)
            return data
        else:
            return loads(json_string)
    except JSONDecodeError as e:
        # Handle JSON decoding errors
        logger.error(f"Error decoding JSON: {e} at {e.__traceback__.tb_lineno}")
        return None

def count_working_days(start_date, end_date, conn, cursor ):
    """
    Count the number of working days between two given dates, excluding weekends (Saturday and Sunday)
    and holidays fetched from the 'Holidays' table in the database.

    Args:
        start_date (datetime.date): The start date.
        end_date (datetime.date): The end date.
        conn: Connection object for the database.
        cursor: Cursor object for executing SQL queries.

    Returns:
        int: The number of working days between start_date and end_date.
    """
    # Define a list of weekdays (Monday = 0, Sunday = 6)
    weekdays = [0, 1, 2, 3, 4]  # Monday to Friday
    
    # Initialize a counter for working days
    working_days = 0
    
    # Iterate through each date between start_date and end_date
    current_date = start_date
    cursor.execute('''
                    SELECT date From Holidays
                    ''')
    holidays = cursor.fetchall()
    while current_date <= end_date:
        # Check if the current date is a weekday
        if current_date.weekday() in weekdays and current_date not in [holiday[0] for holiday in holidays]:
            working_days += 1
        # Move to the next day
        current_date += timedelta(days=1)
    return working_days


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
    