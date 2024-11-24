from django.shortcuts import render

from HillPlainAPI.Loggers import setup_background_logger, setup_sql_logger
import asyncio
from json import dumps, dump, loads, JSONDecodeError
import pytz
import pyodbc
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs
import ast
from .models import BackGroundTaskResult
from django.core.handlers.asgi import ASGIRequest
from django.http import JsonResponse, HttpResponse
import os 
import shutil
import hashlib
import random
import time 
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status


retrySem = asyncio.Semaphore(1)
logger = setup_background_logger()

"""
Handles a deadlock scenario by pausing execution with a randomized delay.

Parameters:
    caller (str): The name of the function or process that encountered the deadlock.
    recordID (int): The ID of the record being processed when the deadlock occurred.

Process:
    - Logs the occurrence of a deadlock and acquires a semaphore (`retrySem`) 
        to manage concurrent deadlock handling.
    - Logs the specific caller and record ID for traceability.
    - Introduces a randomized pause between 3 to 10 seconds, logging each second 
        as it waits.
    - Resumes normal execution after the pause and releases the semaphore.

Exception Handling:
    - Logs any exceptions that occur during the pause for easier debugging.

Notes:
    - This function is asynchronous to allow other tasks to proceed while waiting.
    - The randomized delay aims to prevent repeated deadlock collisions.
"""
async def pauseOnDeadlock(caller, recordID):
    logger = setup_background_logger()
    logger.info('\t\tWaiting for Deadlock Semaphore')
    try:
        async with retrySem:
            logger.info('\t\tAquired Deadlock Semaphore')
            logger.warning(f'DEADLOCK OCCURED WHILE EXECUTING {caller} - Record ID is {recordID}')
            pauseFor = random.randint(3, 10)
            logger.info(f'Pausing for {pauseFor}s')
            for i in range(pauseFor):
                logger.info('\t\tWaiting..........')
                await asyncio.sleep(1)
            logger.info('\tResuming after pause')
    except Exception as e:
        logger.error(f'Exception during pauseOnDeadlock: {str(e)}')
    finally:
        logger.info(f'\t\tDeadlock Semaphore released')

'''
Generates a unique SHA-256 hash ID based on the provided user ID, category ID, and date string.

Parameters:
    vall1 (str): A string representing of a hashable field
    vall2 (str, optional): A string representing of a hashable field
    vall3 (str, optional): A string representing of a hashable field

Returns:
    str: A 64-character hexadecimal string, truncated from the full SHA-256 hash.

Process:
    - Concatenates the `vall1`, `vall2`, and `vall3`, converts 
        the result to lowercase to ensure consistent hashing.
    - Computes the SHA-256 hash of the combined string.
    - Truncates the resulting hexadecimal hash to size characters and returns it.
'''
def hash50(size, vall1, vall2 = None, vall3 = None):
    logger = setup_background_logger()
    # Concatenate the user ID, category ID, and date string
    combined_string = vall1 + (vall2 or '') + (vall3 or '')
    combined_string = combined_string.lower()
    logger.debug(f"Hash String: {combined_string}")
    # Calculate the SHA-256 hash of the combined string
    hash_object = hashlib.sha256(combined_string.encode())
    assert(size >=32 and size <=64)
    # Get the hexadecimal representation of the hash and truncate it to 64 characters
    hash_id = hash_object.hexdigest()[:size]
    logger.debug(f"ID: {hash_id}")
    return hash_id

"""
Generate and serve a zip file for download from the specified folder path.

Parameters:
    folder_path (str, optional): The path of the folder to compress and download. If None, 
     an error response is returned.

Returns:
    HttpResponse: 
        - If folder_path is provided: Returns a downloadable zip file containing the contents 
         of the specified folder.
        - If folder_path is None: Returns an error HttpResponse with a message about incorrect 
         date parameters.
"""
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

"""
Calculate the number of working days between two dates, excluding weekends and any specified holidays.

Args:
    start_date (datetime): The start date.
    end_date (datetime): The end date.
    excludeDays (list, optional): List of dates to exclude (e.g., holidays). Defaults to an empty list.

Returns:
    int: The count of working days between start_date and end_date, excluding weekends and any dates in excludeDays.
"""
def count_working_daysV2(start_date:datetime, end_date: datetime, excludeDays=[] ):
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

'''
Saves the result of a background task to the BackGroundTaskResult table.

Args:
    response (JsonResponse): The response object containing the task's status and message.
    inputData: The data related to the task being saved.
    caller (str): Identifier for the source or function that initiated the task.

Logs the task result and stores it with a timestamp in the database.
'''
def taskResult(response: JsonResponse, inputData, caller: str):
    logger = setup_background_logger()
    logger.info('Saving task result')
    BackGroundTaskResult.objects.create(
        status_code = response.status_code,
        message = response.content.decode() or None,
        data = inputData,
        caller = caller,
        time = time.now()
    )

'''
Reverses the formatted JSON representation of a dictionary for output.

Args:
    data (dict): The dictionary to be reversed.

Returns:
    str: A string of the JSON-formatted dictionary with lines in reverse order.
'''
def reverseForOutput(data:dict):
    data_lines = dumps(data, indent=4).split('\n')
    reversed_data = '\n'.join(data_lines[::-1])
    return reversed_data

"""
Check if a category should be deleted based on its presence in the categories list.

Args:
category_id (str): The ID of the category to check.
categories (list of dict): A list of category dictionaries.

Returns:
bool: True if the category should not be deleted (i.e., it is found in the list), False otherwise.
"""
def check_category_for_deletion(category_id, categories):
    # Loop through each category in the list
    for category in categories:
        # Check if the current category's ID matches the given category ID
        if category['id'] == category_id:
            # If a match is found, return False (do not delete)
            return False
    # If no match is found after checking all categories, return True (delete)
    return True

'''
Converts a byte string into a Python dictionary, handling both URL-encoded 
and JSON-encoded data.

Args:
    byte_string (bytes): The byte string to be converted.

Returns:
    dict or None: The resulting dictionary if conversion is successful, or None if an error occurs.

Logs:
    - Logs the byte string as a string, any intermediate parsing steps, and the final dictionary output.
    - Logs any JSON decoding errors or other exceptions with error messages and line numbers.
'''
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
def count_working_days(start_date, end_date, conn, cursor ):
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

'''
Calculates the current pay cycle range based on the most recent and upcoming weekends.

Returns:
    tuple: A tuple containing the start and end dates of the current pay cycle in 'YYYY-MM-DD' format. 
           The start date is the Sunday two weeks ago, and the end date is the upcoming Saturday.

Steps:
    - Gets the current date.
    - Finds the most recent Sunday as the start of the current week.
    - Adjusts for the pay cycle starting from two Sundays ago.
    - Calculates the end of the pay cycle on the upcoming Saturday.
    - Formats the start and end dates as 'YYYY-MM-DD' strings.
'''
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

'''
Retrieves the current month and year in two-digit formats.

Returns:
    tuple: A tuple containing:
           - month (str): The current month as a two-digit string (e.g., '01' for January).
           - year (str): The last two digits of the current year (e.g., '23' for 2023).

Steps:
    - Gets the current date.
    - Extracts the month, ensuring it's a two-digit string.
    - Extracts the last two digits of the year.
'''
def getMonthYear():
    # Get the current date
    current_date = datetime.now()

    # Extract the month and year
    month = str(current_date.month)
    month = (str(0) + month)[-2:] # ensures 2 digit
    year = str(current_date.year)[2:]
    return month, year

'''
Returns the abbreviation for a given month or the month number, with optional reversal.

Args:
    month (str, optional): The month in two-digit format (e.g., '01'). Defaults to the current month if not provided.
    year (str, optional): The year in two-digit format. Defaults to the current year if not provided.
    reverse (bool, optional): If set to True, returns the month number for a given abbreviation. Defaults to False.

Returns:
    str: The abbreviated month name (e.g., 'Jan' for '01') or the month number (e.g., '01' for 'Jan').

Steps:
    - If `month` is not provided, the current month is used.
    - If `reverse` is False, the month abbreviation is returned; otherwise, the month number is returned.
'''
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

'''
Converts a given datetime from UTC to a specified local timezone (America/Denver by default).

Args:
    dateTime (str or datetime): The datetime to be converted, either as a string or a datetime object.
    format (str, optional): The format to use when parsing the input datetime string. Defaults to '%Y-%m-%dT%H:%M:%SZ'.

Returns:
    datetime: The datetime converted to the local timezone (America/Denver) without timezone information.

Steps:
    - If the input `dateTime` is a string, it's parsed into a datetime object using the specified format.
    - The datetime is first localized to UTC and then converted to the local timezone.
    - The timezone information is removed from the output before returning the converted datetime.
'''
def toMST(date_obj: datetime, time = False):
    if date_obj.tzinfo is None:
        date_obj = date_obj.replace(tzinfo=pytz.UTC)
    else:
        date_obj = date_obj.astimezone(pytz.UTC)
    
    # Convert to Mountain Standard Time (MST)
    mst = pytz.timezone('America/Denver')  # MST is 'America/Denver' in pytz
    
    mst_date_obj = date_obj.astimezone(mst)
    if not time:
        return mst_date_obj.strftime('%Y-%m-%d')
    else: 
        return mst_date_obj.strftime('%Y-%m-%dT%H:%M:%S')
'''
Converts an ISO 8601 duration string to a rounded duration in hours.

Args:
    duration_str (str): An ISO 8601 duration string, typically in the format "PTnHnM" where:
        - "PT" indicates the start of a period of time.
        - "nH" represents hours.
        - "nM" represents minutes.
    Example: "PT1H30M" represents 1 hour and 30 minutes.

Returns:
    float: The total duration converted to hours, rounded to the nearest 15-minute interval.

Steps:
    - Extract the hours and minutes from the input string.
    - Convert the total duration into minutes.
    - Round the total minutes to the nearest 15-minute interval.
    - Convert the rounded minutes back into hours.
'''
def timeDuration(duration_str):
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

"""
Checks if the given date string is within the specified window of days from the current date.

Args:
    date_string (str): A string representing the date in the format '%Y-%m-%dT%H:%M:%SZ'.
    window (int): The number of days to consider for the window.

Returns:
    bool: True if the date is within the window, False otherwise.
"""
def is_within(date_string, window):
    # Convert the date string to a datetime object
    date_object = datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)

    # Get the current date
    current_date = datetime.now(timezone.utc)

    # Calculate the difference between the two dates
    difference = current_date - date_object

    # Check if the difference is less than or equal to 7 days
    return difference <= timedelta(days=window)

'''
Establishes a connection to a Microsoft SQL Server database using pyodbc.

Args:
    None

Returns:
    cursor, conn: A tuple containing:
        - cursor: A pyodbc cursor object used to interact with the database.
        - conn: A pyodbc connection object representing the established connection.

Raises:
    pyodbc.Error: If there is an error during the connection process, the exception is logged and re-raised.

Steps:
    - Sets up the connection string with server information, credentials, and encryption settings.
    - Attempts to connect to the SQL Server database using pyodbc.
    - Returns the cursor and connection objects for further interaction with the database.
    - Logs a critical error if the connection fails.
'''
def sqlConnect():
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
        conn.autocommit = False
        return cursor, conn
    except pyodbc.Error as e:
        logger.critical(f"Error: {e}")
        raise e

"""
Closes the cursor and connection objects.

Args:
    conn: The connection object to be closed.
    cursor: The cursor object to be closed.

Returns:
    int: 1 if the cleanup is successful, 0 otherwise.
"""
def cleanUp(conn, cursor):
    try: 
        cursor.close()
        conn.close()
        return "Completed"
    except pyodbc.Error as e:
        logger.error(f"Error: {str(e)}")
        return "Bad Clean UP"