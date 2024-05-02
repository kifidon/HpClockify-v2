
import requests
import pyodbc
from datetime import datetime, timedelta, timezone
import pytz
import logging
import asyncio 
import httpx
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

def getApiKey():
    API_KEY = 'YWUzMTBiZTYtNjUzNi00MzJmLWFjNmUtYmZlMjM1Y2U5MDY3' # Matt Dixon 
    # API_KEY = 'MmRiYWE2NmMtOTM3My00MjFlLWEwOTItNWEzZTY2Y2YxNDQx' # Shawn Applejohn 
    # API_KEY = 'ZjZhM2MwZmEtOTFiZi00MWE0LTk5NTMtZWUxNGJjN2FmNmQy' # Timmy Ifidon 
    return API_KEY

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
    
def getWorkspaces(key):
    """
    Retrieves the workspaces associated with the provided API key.

    Args:
        key (str): The API key for accessing the Clockify API.

    Returns:
        dict or dict(): A dictionary containing workspace names as keys and their corresponding IDs as values,
                      or dict() if an error occurs.
    """    
    headers = {
    'X-Api-Key': key,  
    }
    url = 'https://api.clockify.me/api/v1/workspaces'
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        workSpace = {workspaces['name']:workspaces['id'] for workspaces in response.json()}
        return workSpace
    else:
        print(f"Error: {response.status_code}, {response.text}")
        return dict()

def getWorkspaceUsers( workspaceId, key):
    """
    Retrieves the users associated with a specific workspace.

    Args:
        workspaceId (str): The ID of the workspace.
        key (str): The API key for accessing the Clockify API.

    Returns:
        dict or dict(): A dictionary containing user details, or dict() if an error occurs.
    """
    headers = {
        'X-Api-Key': key
    }
    url = f'https://api.clockify.me/api/v1/workspaces/{workspaceId}/users?page-size=150'
    response = requests.get(url, headers= headers)
    if response.status_code == 200:
        users = response.json()
        return users
    else:
        print(f"Error: {response.status_code}, {response.text}")
        return dict()

def getProjects(workspaceId, key, page =1):
    """
    Retrieves the projects associated with a specific workspace.

    Args:
        workspaceId (str): The ID of the workspace.
        key (str): The API key for accessing the Clockify API.

    Returns:
        dict or dict(): A dictionary containing project details, or dict() if an error occurs.
    """    
    headers = {
        'X-Api-Key': key
    }
    url = f'https://api.clockify.me/api/v1/workspaces/{workspaceId}/projects?page={page}&archived=false'
    response = requests.get(url, headers= headers)
    if response.status_code == 200:
        projects = response.json()
        return projects
    else:
        print(f"Error: {response.status_code}, {response.text}")
        return dict()

async def FindTimesheet(workspaceId, key, timeId, status, page):
    url = f"https://api.clockify.me/api/v1/workspaces/{workspaceId}/approval-requests?status={status}&page={page}&page-size=200"
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers={'X-Api-Key': key})
        if response.status_code == 200:
            for timesheet in response.json():
                if timesheet['approvalRequest']['id'] == timeId:
                    return timesheet['entries']
            # Not found on this page, try next page
            return []
        else:
            raise Exception(f"Failed to pull Data From Clockify: {response.json()}")

async def getEntryForApproval(workspaceId, key, timeId, status='APPROVED', page = 1):
    """
    Retrieves the requests (Time Sheet) for a specific workspace as well as the approval status of the request 

    Args:
        workspaceId (str): The ID of the workspace.
        key (str): The API key for accessing the Clockify API.

    Returns:
        dict or dict(): A dictionary containing approved request details, or dict() if an error occurs.
    """
    if status == 'PENDING':
        return []
    headers = {
        'X-Api-Key': key
    }
    url = f"https://api.clockify.me/api/v1/workspaces/{workspaceId}/approval-requests?status={status}&page={page}&page-size=200" 
    logging.info(f'INFO: {url}')   
    async with httpx.AsyncioClient() as client:
        response = client.get(url, headers=headers)
        if response.status_code == 200:
            for page_number in range(1, 6):  # Iterate from page 1 to page 5 asynchronously
                tasks = [
                    FindTimesheet(workspaceId, key, timeId, status, page_number)
                    for page_number in range(1, 6)
                ]
            entries = await asyncio.gather(*tasks)
            if entries:
                    return entries
            return [] 
            
        else:
            raise(pyodbc.DatabaseError(f"Failed to pull Data From Clockify: \n{response.json()}"))
    # #
    # else:
    #         print(f"Error: {response.status_code}, {response.text}")
    #         output.append({})
    # return output

def getClients(workspaceId, key): 
    """
    Retrieves the clients associated with a specific workspace.

    Args:
        workspaceId (str): The ID of the workspace.
        key (str): The API key for accessing the Clockify API.

    Returns:
        dict or dict(): A dictionary containing client details, or dict() if an error occurs.
    """
    headers = {
        'X-Api-Key': key
    }
    url = f'https://api.clockify.me/api/v1/workspaces/{workspaceId}/clients'
    response = requests.get(url, headers=headers)
    if response.status_code==200:
        return response.json()
    else:
        print(f"Error: {response.status_code}, {response.text}")
        return dict()

def getPolocies(workspaceId, key):
    """
    Retrieves the policies associated with a specific workspace.

    Args:
        workspaceId (str): The ID of the workspace.
        key (str): The API key for accessing the Clockify API.

    Returns:
        dict or dict(): A dictionary containing policy details, or dict() if an error occurs.
    """
    headers = {
        'X-Api-Key': key
    }
    url = f'https://pto.api.clockify.me/v1/workspaces/{workspaceId}/policies?status=ALL'
    response = requests.get(url, headers=headers)
    if response.status_code==200:
        return response.json()
    else:
        print(f"Error: {response.status_code}, {response.text}")
        return dict()

def getTimeOff(workspaceId, page =1, startDate = "None", endDate = "None", window = -1):
    """
    Retrieves time off requests for a specific workspace within a given window.

    Args:
        workspaceId (str): The ID of the workspace.
        startDate (str): Date in the form YYYY-mm-DD.

    Returns:
        dict or dict(): A dictionary containing time off request details, or dict() if an error occurs.
    """
    key = getApiKey()
    if window != -1 or (startDate == "None" and endDate == "None"): 
        # mst_timezone = pytz.timezone('US/Mountain')
        # endDate = datetime.now(mst_timezone) 
        endDateFormated =   '2024-12-31T23:59:59.999999Z'
        # endDateFormated = endDate.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        startDateFormated = '2024-01-01T00:00:00.000000Z'
    else: 
        startDateFormated = startDate + "T00:00:00.000000Z" 
        endDateFormated   = endDate   + "T23:59:59.599999Z" 
    headers = {
        'Content-Type': 'application/json',
        'X-Api-Key': key
    }
    
    cursor, conn = sqlConnect()
    cursor.execute('select id from EmployeeUser')
    users = cursor.fetchall()
    cleanUp(conn=conn , cursor= cursor)
    request_body = {
        "end": endDateFormated,
        "page": page,
        "page-size": 30,
        "start": startDateFormated,
        "statuses": ["ALL"],
        "userGroups": [],
        "users": [user[0] for user in users]
    }
    url = f'https://pto.api.clockify.me/v1/workspaces/{workspaceId}/requests'
    response = requests.post(url=url, json=request_body, headers=headers)
    if response.status_code == 200:
        return response.json()
    else: 
        print(f"Error: {response.status_code}, {response.reason}")
        return dict()
    
def getHolidays(workspaceId ):
    key = getApiKey()
    headers = {
        'X-Api-Key': key
    }
    url = f"https://pto.api.clockify.me/v1/workspaces/{workspaceId}/holidays"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else: 
        print(f"Error: {response.status_code}, {response.reason}")
        return dict()

def getUserGroups(workspaceID):
    key = getApiKey()
    headers = {
        'X-Api-Key': key
    }
    url = f"https://api.clockify.me/api/v1/workspaces/{workspaceID}/user-groups"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else: 
        print(f"Error: {response.status_code}, {response.reason}")
        return dict()
'''
def getAttendance(workspaceId, startDate="2024-01-01T00:00:00Z", endDate="2024-03-01T23:59:59.999Z", page=1):
    key = getApiKey()
    headers = {
        'Content-Type': 'application/json',
        'X-Api-Key': key
    }
    request_body = {
        "approvalState": "APPROVED",
        "sortOrder": "ASCENDING",
        "dateRangeStart": startDate,
        "dateRangeEnd": endDate,
        "users": {
            "ids": [],
            "contains": "CONTAINS",
            "status": "ALL"
        },
        "userGroups": {
            "ids": ["65ca72f20c80de6b9558d332"],
            "contains": "CONTAINS",
            "status": "ALL"
        },
        "attendanceFilter": {
            "page": page,
            "pageSize": 50,
            "sortColumn": "DATE",
            
        }
    }
    url = f"https://reports.api.clockify.me/v1/workspaces/{workspaceId}/reports/attendance"
    response = requests.post(url = url, json= request_body, headers= headers)
    if response.status_code == 200:
        return response.json()
    else: 
        print(f"Error: {response.status_code} \n{response.reason}:\n\t{response.text}")
        return dict()

def getStaleApproval(workspaceId, key, page = 1):
    """
    Retrieves the Withdranw approval requests for deletion requests for a specific workspace.

    Args:
        workspaceId (str): The ID of the workspace.
        key (str): The API key for accessing the Clockify API.

    Returns:
        dict or dict(): A dictionary containing withdrawn request details, or dict() if an error occurs.
    """
    headers = {
        'X-Api-Key': key
    }
    url = f'https://api.clockify.me/api/v1/workspaces/{workspaceId}/approval-requests?status=WITHDRAWN_APPROVAL&page={page}&page-size=50'    
    response = requests.get(url, headers= headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code}, {response.text}")
        return dict()
'''
def getApprovedRequests(workspaceId, key, page = 1, status = 'APPROVED'):
    """
    Retrieves the requests (Time Sheet) for a specific workspace as well as the approval status of the request 

    Args:
        workspaceId (str): The ID of the workspace.
        key (str): The API key for accessing the Clockify API.

    Returns:
        dict or dict(): A dictionary containing approved request details, or dict() if an error occurs.
    """
    output = []  # Initialize an empty list
    headers = {
        'X-Api-Key': key
    }
    url = f"https://api.clockify.me/api/v1/workspaces/{workspaceId}/approval-requests?status={status}&page={page}&page-size=5"    
    response = requests.get(url, headers=headers)
    # if response.json()['approvalRequest']['owner']['userId'] == '660431c45599d034112545ed':
    #     pass
    if response.status_code == 200:
        return response.json()  # Append JSON data to the list
    else:
            print(f"Error: {response.status_code}, {response.text}")
            output.append({})
    return output

def main():
    pass
if __name__ == "__main__":
    main()