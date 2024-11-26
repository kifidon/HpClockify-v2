
import requests
import pyodbc
from enum import Enum
import asyncio 
import httpx
import time
from json import loads
from datetime import datetime, timedelta
from httpcore import ConnectTimeout
from json import dumps
# from ..views import  dumps, sqlConnect, cleanUp
from HillPlainAPI.Loggers import setup_background_logger
from Clockify.models import Employeeuser  
from asgiref.sync import sync_to_async

logger = setup_background_logger()

MAX_RETRIES = 3
DELAY = 2 #seconds 

def getApiKey():
    API_KEY = 'YWUzMTBiZTYtNjUzNi00MzJmLWFjNmUtYmZlMjM1Y2U5MDY3' # Matt Dixon 
    # API_KEY = 'MmRiYWE2NmMtOTM3My00MjFlLWEwOTItNWEzZTY2Y2YxNDQx' # Shawn Applejohn 
    # API_KEY = 'ZjZhM2MwZmEtOTFiZi00MWE0LTk5NTMtZWUxNGJjN2FmNmQy' # Timmy Ifidon 
    return API_KEY

class Status(Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    # WITHDRAWN_SUBMISSION = "WITHDRAWN_SUBMISSION"
    WITHDRAWN_APPROVAL = "WITHDRAWN_APPROVAL"
    # REJECTED = "REJECTED"
    
async def FindTimesheet(workspaceId, key, timeId, status, page, entry = False, expense = False):
    while page < 10:
        if entry and expense:
            logger.error("AssertionError('Bad Method. Call for expense and entry data seperatly')")
            return []
        logger.info(f'FindTimesheet called for {timeId} on page {page} ')
        url = f"https://api.clockify.me/api/v1/workspaces/{workspaceId}/approval-requests?status={status}&page={page}&page-size=20&sort-column=UPDATED_AT"
        async with httpx.AsyncClient(timeout=300) as client:
            response = await client.get(url, headers={'X-Api-Key': key})
            if response.status_code == 200:
                for timesheet in response.json():
                    if timesheet['approvalRequest']['id'] == timeId:
                        logger.info(f'Timesheet found on page {page}')
                        if entry:
                            logger.debug(f'Data found:\n{dumps(timesheet['entries'], indent = 4)}')
                            logger.debug(f'FindTimesheet executed {page}')
                            return timesheet['entries']
                        elif expense:
                            logger.debug(f'Data found: \n{dumps(timesheet['expenses'], indent = 4)}')
                            logger.debug(f'FindTimesheet executed {page}')
                            return timesheet['expenses']
                        else:
                            return []
                # Not found on this page, try next page
                logger.info(f'FindTimesheet executed - Not Found in range {page}')
                page += 1
            else:
                raise Exception(f"Failed to pull Data From Clockify: {response.status_code} {response.text}")
    return []

async def getDataForApproval(workspaceId, key, timeId, status='APPROVED', entryFlag = False, expenseFlag = False):
    """
    Retrieves the requests (Time Sheet) for a specific workspace as well as the approval status of the request 

    Args:
        workspaceId (str): The ID of the workspace.
        key (str): The API key for accessing the Clockify API.

    Returns:
        dict or dict(): A dictionary containing approved request details, or dict() if an error occurs.
    """    
    retries= 0

    async def delayed_find_timesheet(workspaceId, key, timeId, status, page_number, delay): #que requests 
        await asyncio.sleep(delay)
        return await FindTimesheet(workspaceId, key, timeId, status, page_number, entryFlag , expenseFlag )

    tasks = []
    delay_between_tasks = 1
    while retries < MAX_RETRIES:
        try:
            tasks = []
            # for page_number in range(1, 7):  # Iterate from page 1 to page 6 asynchronously
            for page_number in range(1, 2):  # First page of recent changes 
                # findTimesheetAsync = sync_to_async(FindTimesheet)   
                tasks.append(
                    asyncio.create_task(delayed_find_timesheet(workspaceId, key, timeId, status, page_number, delay_between_tasks * page_number))
                )
            dataAll = await asyncio.gather(*tasks)
            
            if dataAll != 0:
                output = []
                for data in dataAll:
                    logger.info('Temp store Entry data in dict() object')
                    if data is not None:
                        output.extend(data)           
                return output 
            else:
                raise(pyodbc.DatabaseError(f"Failed to pull Data From Clockify: TimeSheet not found/pulled"))
        except ConnectTimeout as e:
            logger.warning(f' Request timed out...Retrying {retries}/{MAX_RETRIES}')
            time.sleep(DELAY+ retries)
            logger.info(f' Sleeping for {DELAY + retries}s')
            retries += 1
        except httpx.ReadTimeout as e:
            logger.warning(f' Request timed out...Retrying {retries}/{MAX_RETRIES}')
            time.sleep(DELAY+ retries)
            logger.info(f' Sleeping for {DELAY + retries}s')
            retries += 1
        except httpx.TimeoutException as e:
            logger.warning(f' Request timed out...Retrying {retries}/{MAX_RETRIES}')
            time.sleep(DELAY+ retries)
            logger.info(f' Sleeping for {DELAY + retries}s')
            retries += 1
        except TimeoutError as e:
            logger.warning(f' Request timed out...Retrying {retries}/{MAX_RETRIES}')
            time.sleep(DELAY+ retries)
            logger.info(f' Sleeping for {DELAY + retries}s')
            retries += 1
        except Exception as e:
            logger.error(f' {str(e)} at line {e.__traceback__.tb_lineno} in \n\t{e.__traceback__.tb_frame}')
            raise e
    logger.error(f' Max Retries reached')
    raise ConnectTimeout

async def getTimeOff(workspaceId: str, startDate:str , endDate: str, page:int ):
    """
    Retrieves time off requests for a specific workspace within a given window.

    Args:
        workspaceId (str): The ID of the workspace.
        startDate (str): Date in the form YYYY-mm-DD.

    Returns:
        dict or dict(): A dictionary containing time off request details, or dict() if an error occurs.
    """
    try:  
        key = getApiKey()
        startDateFormated = startDate + "T00:00:00.000000Z" 
        endDateFormated   = endDate   + "T23:59:59.599999Z" 
        headers = {
            'Content-Type': 'application/json',
            'X-Api-Key': key
        }
        emp = await sync_to_async(list)(Employeeuser.objects.all())

        request_body = {
            "end": endDateFormated,
            "page": page,
            "page-size": 200,
            "start": startDateFormated,
            "statuses": ["ALL"],
            
            "users": [e.id for e in emp]
        }
        # logger.debug(dumps(request_body))
        url = f'https://api.clockify.me/api/v1/workspaces/{workspaceId}/time-off/requests'
        response = requests.post(url=url, json=request_body, headers=headers)
        # logger.debug(f"StatusCode: {response.text}")
        if response.status_code == 200:
            return response.json()
        else: 
            logger.error(f"Error: {response.status_code}, {response.reason}")
            return dict()
    except Exception as e: 
        logger.critical(f'{str(e)} - ({e.__traceback__.tb_lineno})')
        raise e
  
async def getTimesheets(workspaceId, key, page = 1):
    
    """
    Retrieves the requests (Time Sheet) for a specific workspace as well as the approval status of the request 

    Args:
        workspaceId (str): The ID of the workspace.
        key (str): The API key for accessing the Clockify API.

    Returns:
        dict or dict(): A dictionary containing approved request details, or dict() if an error occurs.
    """
    try: 
        output = []  # Initialize an empty list
        task = []
        headers = {
            'X-Api-Key': key
        }
        async with httpx.AsyncClient() as client:
            for status in Status:
                logger.debug(f'Status: {status.value}')
                url = f"https://api.clockify.me/api/v1/workspaces/{workspaceId}/approval-requests?status={status.value}&page={page}&page-size=10&sort-column=UPDATED_AT"    
                task.append(client.get(url, headers=headers))
    
            results = await asyncio.gather(*task)
            for result in results:
                if result.status_code == 200:
                    output.extend(result.json())
                else:
                    logger.error(f" {result.status_code}, {result.text}")
                    raise ConnectionError
            return output
    except Exception as e:
       logger.error(f'({e.__traceback__.tb_lineno}) in getTimesheet- {str(e)}')
       raise e


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
# Comment
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
    url = f'https://api.clockify.me/api/v1/workspaces/{workspaceId}/projects?page={page}&archived=false&page-size=500'
    response = requests.get(url, headers= headers)
    if response.status_code == 200:
        projects = response.json()
        return projects
    else:
        print(f"Error: {response.status_code}, {response.text}")
        return dict()

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
    logger.debug(url)
    response = requests.get(url, headers=headers)
    if response.status_code==200:
        return response.json()
    else:
        logger.critical(f"Error: {response.status_code}, {response.text}")
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

def getCategories(workspaceId, page):
    logger.info(f' Begining Clockify data pull')
    key = getApiKey()
    headers = {
        'X-Api-Key': key
    }
    url = f'https://api.clockify.me/api/v1/workspaces/{workspaceId}/expenses/categories'
    response = requests.get(url=url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        raise(Exception('Failed to pull from Clockify'))
    

def getDetailedEntryReport(workspaceId):
    logger.info('Pulling Detailed Expense Report')
    try:
        print('Pulling Detailed Expense Report')
        key = getApiKey()
        headers = {
            "X-Api-Key": key
        }
        url = f'https://reports.api.clockify.me/v1/workspaces/{workspaceId}/reports/detailed'
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        #convert to strings
        today = today.strftime('%Y-%m-%dT00:00:00.000Z')
        yesterday = yesterday.strftime('%Y-%m-%dT00:00:00.000Z') 
        requestBody = {
            "approvalState":  "ALL",
            "dateRangeEnd": today,
            "dateRangeStart": yesterday,
            "dateRangeType": "YESTERDAY",
            "exportType": "JSON",
            "sortOrder": "ASCENDING",
            "detailedFilter": {
                "options": {
                    "totals": "CALCULATE"
                },
                "page": 1,
                "pageSize": 200,
                "sortColumn": "USER"
            }
        }
        response = requests.post(url=url, headers=headers, json=requestBody)
        if response.status_code== 200: 
            output = loads(response.content)
            return output 
        else: 
            logger.critical(response.text)
            print(response.text)
    except Exception as e :
        logger.error(f"({e.__traceback__.tb_lineno}) - {str(e)}")
        raise e
    
def main():

    # detailedEntryReport('65c249bfedeea53ae19d7dad')
    pass
if __name__ == "__main__":
    main()