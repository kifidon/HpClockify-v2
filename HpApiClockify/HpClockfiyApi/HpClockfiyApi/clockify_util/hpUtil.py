from .. Loggers import setup_background_logger
import asyncio
from json import dumps, dump, loads, JSONDecodeError
import pytz
import pyodbc
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs
import ast
from ..models import BackGroundTaskResult
from django.http import JsonResponse, HttpResponse
import os 
import shutil
import hashlib
import random

retrySem = asyncio.Semaphore(1)

async def pauseOnDeadlock(caller, recordID):
    logger = setup_background_logger()
    logger.info('\t\tWaiting for Deadlock Semaphore')
    try:
        async with retrySem:
            logger.info('\t\tAquired Deadlock Semaphore')
            logger.warning(f'DEADLOCK OCCURED WHILE EXECUTING {caller} - Record ID is {recordID}')
            pauseFor = random.randint(1, 5)
            logger.info(f'Pausing for {pauseFor}s')
            for i in range(pauseFor):
                logger.info('\t\tWaiting..........')
                await asyncio.sleep(1)
            logger.info('\tResuming after pause')
    except Exception as e:
        logger.error(f'Exception during pauseOnDeadlock: {str(e)}')
    finally:
        logger.info(f'\t\tDeadlock Semaphore released')


def create_hash(user_id, category_id, date_string):
    # Concatenate the user ID, category ID, and date string
    combined_string = user_id + category_id + date_string
    combined_string = combined_string.lower()
    # Calculate the SHA-256 hash of the combined string
    hash_object = hashlib.sha256(combined_string.encode())
    
    # Get the hexadecimal representation of the hash and truncate it to 64 characters
    hash_id = hash_object.hexdigest()[:64]
    
    return hash_id


def hash50(vall1, vall2 = None, vall3 = None):
    logger = setup_background_logger()
    # Concatenate the user ID, category ID, and date string
    combined_string = vall1 + (vall2 or '') + (vall3 or '')
    combined_string = combined_string.lower()
    logger.debug(f"Hash String: {combined_string}")
    # Calculate the SHA-256 hash of the combined string
    hash_object = hashlib.sha256(combined_string.encode())
    
    # Get the hexadecimal representation of the hash and truncate it to 64 characters
    hash_id = hash_object.hexdigest()[:45]
    logger.debug(f"ID: {hash_id}")
    return hash_id

def download_text_file(folder_path = None):
    
    if folder_path:
        temp_dir = f'{folder_path}_tmp'
        os.makedirs(temp_dir, exist_ok=True)
        # Compress the folder into a zip file
        shutil.make_archive(temp_dir, 'zip', folder_path)
        # Get the zip file path
        zip_file_path = f'{temp_dir}.zip'

        with open(zip_file_path, 'rb') as file:
            response = HttpResponse(file.read(), content_type='application/zip')
            response['Content-Disposition'] = f'attachment; filename="{os.path.basename(zip_file_path)}"'
        shutil.rmtree(temp_dir)
        os.remove(zip_file_path)
        return response
    return HttpResponse( content='Could not pull billing report. Are you sure the date parameters are in the correct form?\nReview Logs for more detail @ https://hillplain-api.ngrok.app/')


def count_working_daysV2(start_date:datetime, end_date: datetime, excludeDays=[] ):
    """
    Count the number of working days between two given dates, excluding weekends (Saturday and Sunday)
    and holidays fetched from the 'Holidays' table in the database.

    Args:
        start_date (datetime.date): The start date.
        end_date (datetime.date): The end date.
        

    Returns:
        int: The number of working days between start_date and end_date.
    """
    # Define a list of weekdays (Monday = 0, Sunday = 6)
    weekdays = [0, 1, 2, 3, 4]  # Monday to Friday
    
    # Initialize a counter for working days
    working_days = 0
    
    # Iterate through each date between start_date and end_date
    current_date = start_date
    
    while current_date <= end_date:
        # Check if the current date is a weekday
        if current_date.weekday() in weekdays and current_date not in excludeDays:
            working_days += 1
        # Move to the next day
        current_date += timedelta(days=1)
    return working_days


def taskResult(response: JsonResponse, inputData, caller: str):
    logger = setup_background_logger()
    logger.info('Saving task result')
    BackGroundTaskResult.objects.create(
        status_code = response.status_code,
        message = response.content.decode() or None,
        data = inputData,
        caller = caller,
        time = timeZoneConvert(get_current_time(), '%Y-%m-%d %H:%M:%S')
    )


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
    logger = setup_background_logger()
    try:
        logger.debug(f"byte to string - {byte_string}")
        # Decode the byte string into a regular string
        json_string = byte_string.decode('utf-8')

        # Parse the JSON string into a Python dictionary
        data = parse_qs(json_string)
        if data:
            for key, value in data.items():
                try:
                    data[key] = ast.literal_eval(value[0])
                except Exception:
                    data[key] = value[0]
            logger.debug(f"Output dict - {data}")
            return data
        else:
            output = loads(json_string)
            logger.debug(dumps(output, indent=4))
            return output
    except JSONDecodeError as e:
        # Handle JSON decoding errors
        logger.error(f"Error decoding JSON: {e} at {e.__traceback__.tb_lineno}")
        return None
    except Exception as e:
        logger.error(f"({e.__traceback__.tb_lineno} - {str(e)}")
        raise e

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
    month = (str(0) + month)[-2:] # ensures 2 digit
    year = str(current_date.year)[2:]
    return month, year

def getAbbreviation(month = None, year = None, reverse = False ):
    Abbreviation = {
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

    monthNum = {
        'Jan': '01',
        'Feb': '02',
        'Mar': '03',
        'Apr': '04',
        'May': '05',
        'Jun': '06',
        'Jul': '07',
        'Aug': '08',
        'Sep': '09',
        'Oct': '10',
        'Nov': '11',
        'Dec': '12'
    }

    if month is None:
        month, year = getMonthYear() # current month 
    if not reverse: 
        return f"{ Abbreviation.get(month, f'Invalid Month: {month}')}"
    else:
        return f"{ monthNum.get(month, f'Invalid Month: {month}')}"


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
        logger = setup_background_logger()
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
        logger.critical(f"Error: {e}")
        raise e

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
    