
import requests
import pyodbc
import asyncio 
import httpx
import time
from httpcore import ConnectTimeout
from .hpUtil import get_current_time , logging, dumps, sqlConnect, cleanUp

MAX_RETRIES = 3
DELAY = 2 #seconds 

def getApiKey():
    # API_KEY = 'YWUzMTBiZTYtNjUzNi00MzJmLWFjNmUtYmZlMjM1Y2U5MDY3' # Matt Dixon 
    # API_KEY = 'MmRiYWE2NmMtOTM3My00MjFlLWEwOTItNWEzZTY2Y2YxNDQx' # Shawn Applejohn 
    API_KEY = 'ZjZhM2MwZmEtOTFiZi00MWE0LTk5NTMtZWUxNGJjN2FmNmQy' # Timmy Ifidon 
    return API_KEY

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
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(url, headers={'X-Api-Key': key})
        if response.status_code == 200:
            for timesheet in response.json():
                if timesheet['approvalRequest']['id'] == timeId:
                    logging.info(f'{get_current_time()} - INFO: Timesheet found on page {page}')
                    # print(dumps(timesheet['entries'], indent = 4))
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
    retries= 0
    while retries < MAX_RETRIES:
        try:
            tasks = []
            for page_number in range(1, 7):  # Iterate from page 1 to page 5 asynchronously
                tasks.append(
                    FindTimesheet(workspaceId, key, timeId, status, page_number)
                )
            entries = await asyncio.gather(*tasks)
            
            if entries != 0:
                output = []
                for entry in entries:
                    output.extend(entry)           
                return output 
            else:
                raise(pyodbc.DatabaseError(f"Failed to pull Data From Clockify: TimeSheet not found/pulled"))
        except ConnectTimeout as e:
            logging.warning(f'{get_current_time()} - WARNING: Request timed out...Retrying {retries}/{MAX_RETRIES}')
            time.sleep(DELAY+ retries)
            logging.info(f'{get_current_time()} - INFO: Sleeping for {DELAY + retries}s')
            retries += 1
        except httpx.ReadTimeout as e:
            logging.warning(f'{get_current_time()} - WARNING: Request timed out...Retrying {retries}/{MAX_RETRIES}')
            time.sleep(DELAY+ retries)
            logging.info(f'{get_current_time()} - INFO: Sleeping for {DELAY + retries}s')
            retries += 1
        except httpx.TimeoutException as e:
            logging.warning(f'{get_current_time()} - WARNING: Request timed out...Retrying {retries}/{MAX_RETRIES}')
            time.sleep(DELAY+ retries)
            logging.info(f'{get_current_time()} - INFO: Sleeping for {DELAY + retries}s')
            retries += 1
        except TimeoutError as e:
            logging.warning(f'{get_current_time()} - WARNING: Request timed out...Retrying {retries}/{MAX_RETRIES}')
            time.sleep(DELAY+ retries)
            logging.info(f'{get_current_time()} - INFO: Sleeping for {DELAY + retries}s')
            retries += 1
        except Exception as e:
            logging.error(f'{get_current_time()} - ERROR: {str(e)} at line {e.__traceback__.tb_lineno} in \n\t{e.__traceback__.tb_frame}')
            raise e
    logging.error(f'{get_current_time()} - ERROR: Max Retries reached')
    raise ConnectTimeout

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