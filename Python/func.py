import pyodbc
import pytz
from datetime import datetime

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
        minutes = int( (duration_str.split('M'))[0] )/60
    return( hours + minutes)

def rowToJson(row):
    json_data = {}
    for column_name, value in zip(row.cursor_description, row):
        # Extract column name
        name = column_name[0]

        # Convert to snake_case format
        snake_case_name = ''.join(['_' + c.lower() if c.isupper() else c for c in name]).lstrip('_')

        # Convert value to string and add to JSON dictionary
        json_data[snake_case_name] = str(value)

    return json_data

def errorToJson(exc):
    json_data = {
        "error_class": str(exc.__class__),
        "filename": exc.__traceback__.tb_frame.f_code.co_filename,
        "function_name": exc.__traceback__.tb_frame.f_code.co_name,
        "line_number": exc.__traceback__.tb_lineno,
        "error_message": str(exc)
    }
    return json_data
