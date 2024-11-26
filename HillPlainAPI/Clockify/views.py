from django.shortcuts import render
from django.shortcuts import render
from django.http import JsonResponse
from django.core.handlers.asgi import ASGIRequest
from rest_framework.decorators import api_view
from django.views.decorators.csrf import csrf_exempt
from django.db import  utils  #, transaction
from . import *
from .models import*
from asgiref.sync import sync_to_async
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response 
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from .serializers import *
from Utilities.views import *
from Utilities.clockify_util.QuickBackupV3 import ClientEvent, PolicyEvent, eventSelect
from Utilities.clockify_util.ClockifyScheduledTasks import BankedTime, updateSalaryVacation
from HillPlainAPI.Loggers import setup_server_logger
import asyncio
import httpx

loggerLevel = 'DEBUG'
logger = setup_server_logger()
saveTaskResult = sync_to_async(taskResult, thread_sensitive=True)

async def asave(serializer):
    if serializer.instance:  # Update path for an existing instance
        await sync_to_async(serializer.instance.save)()
    else:  # Create path for a new instance
        await sync_to_async(serializer.save)()

'''
Function Description: 
    Authenticates the secret key given from clockify with the one stored in this file. This impliments a minimum security layer to the databse.
    Impliment HMAC validation in a future update

Param: 
    request(ASGIRequest): request sent to endpoint where this function is called 
    secret(str): secret key used to authenticate the request 

Returns: 
    Boolean (True/False) on authentication 
'''
def aunthenticateRequst(request: ASGIRequest, secret: str): 
    logger.info('Validating Request...')
    signature = request.headers.get('Clockify-Signature') 
    if secret == signature:
        logger.info('Request Validated!')
        return True
    else: 
        logger.debug('Invalid Request')
        return False


'''
Function Description: processTimesheet
    This function processes and updates a timesheet entry based on the provided input data. It performs the following steps:

    Retrieve or Initialize Timesheet:
     - Tries to retrieve an existing Timesheet object using the primary key from inputData['id'].
     - If the timesheet does not exist, a new instance is created using the provided data.
    Serialize and Validate Data:
     - Uses a serializer to validate the timesheet data.
     - If the data is valid, the timesheet is saved and a JSON response is returned with the serialized data and an HTTP 202 status.
     - If invalid, returns a JSON response containing error messages with an HTTP 400 status.
    Handle Integrity Errors:
     - Catches IntegrityError exceptions that may arise during the save operation.
     - If a primary key conflict occurs, returns a conflict response (HTTP 409), indicating the timesheet ID already exists.
     - If a foreign key violation occurs, returns a response with an HTTP 406 status, suggesting the data violates foreign key constraints.
     - Error Logging:

Logs each step and error occurrence to help track data processing and potential issues.
Unhandled exceptions are raised after being logged for further debugging.
Note: 
    A transaction.atomic() context is noted for future implementation, which would allow all database actions to be rolled back in case of any failure.
'''
def processTimesheet(inputData): 
    # with transaction.atomic(): # impliment this in the future
    try: 
        try:
            timesheet = Timesheet.objects.get(pk=inputData['id'])
            serializer = TimesheetSerializer(instance= timesheet, data = inputData)
        except Timesheet.DoesNotExist: # this means the timesheet failed in the newTimeSheet function 
            serializer = TimesheetSerializer(data=inputData)
            logger.warning(f'Adding new timesheet on update function. Timesheet { inputData["id"] }')
        if serializer.is_valid():
            serializer.save()
            response = JsonResponse(data={
                                    'timesheet':serializer.validated_data
                                }, status = status.HTTP_202_ACCEPTED)
            logger.info(f'UpdateTimesheet:{dumps(inputData["id"])}{response.status_code}')
            return response
        else: 
            response = JsonResponse(data=serializer.error_messages, status=status.HTTP_400_BAD_REQUEST)
            logger.error(f'UpdateTimesheet:{dumps(inputData["id"])}{response.status_code}')
            return response
    except utils.IntegrityError as e:
        if 'PRIMARY KEY constraint' in str(e): 
            response = JsonResponse(data={'Message': f'Cannot create new Timesheet because id {inputData["id"]} already exists'}, status=status.HTTP_409_CONFLICT, safe=False)
            logger.error(f'Cannot create new Timesheet because id {inputData["id"]} already exists')
            taskResult(response, inputData, 'New Timesheet Function')
        elif('FOREIGN KEY') in str(e): # maybe include calls to update and try again in the future 
            response = JsonResponse(data={'Message': f'Cannot create new Timesheet data includes Foregin Constraint Violation'}, status=status.HTTP_406_NOT_ACCEPTABLE, safe=False)
            logger.error(response.content)
            taskResult(response, inputData, 'New Timesheet Function')
        else:
            raise e
    except Exception as e: 
        logger.error(f'Unknown error ({e.__traceback__.tb_lineno}): {str(e)}')
        raise e
aprocessTimesheet = sync_to_async(processTimesheet, thread_sensitive=False)
updateTimesheetSemaphore = asyncio.Semaphore(3)

'''
Function Description: 
    Updates the status of an approval timesheet. Asyncrhonously calls the update/insert functions for Entry's and, sequentially, Expenses while
    Timesheet update is being done. the Entry and Expense functions can be offloaded to a different host server or a different port on the same 
    server. This keeps the repsonse time of this function under 8000ms. Due to Clockify rate limiting, Entry and Expense functions are cascaded
    to avoid crashing or lost data.

    If any error occurs then save the status code and optional message in the database table 'BackGroundTaskDjango'. Transactions are not atomic 

Param: 
    request(ASGIRequest): Request sent to endpoint from client 

Returns: 
    response (JSONResponse): Communicates back to the client the result of the request. Usually just a string or an echo of the request 
'''
@csrf_exempt
async def TimesheetsView(request:ASGIRequest):
    secret = 'me1lD8vSd5jqmBeaO2DpZvtQ2Qbwzrmy' #update key
    secret2 = 'Qzotb4tVT5QRlXc3HUjwZmkgIk58uUyK' #new timesheet key
    if not (aunthenticateRequst(request, secret) or aunthenticateRequst(request, secret2)):
        response = JsonResponse(data={'Invalid Request': 'SECURITY ALERT'}, status=status.HTTP_423_LOCKED)
        await saveTaskResult(response, dumps(loads(request.body)), 'UpdateTimesheet Function')
        return response
    if request.method != 'POST':
        response = JsonResponse(data={'Message': f'Method {request.method} not allowed'}, status = status.HTTP_405_METHOD_NOT_ALLOWED)
        await saveTaskResult(response, dumps(loads(request.body)), 'UpdateTimesheet Function')
        return response
    
    logger = setup_server_logger(loggerLevel)
    logger.info(f'{request.method}: updateTimesheet')
    try: 
        inputData = loads(request.body)
        logger.info('Waiting for Update Timesheet Semahore')
        async with updateTimesheetSemaphore:
            logger.info('Aquired Update Timesheet Semahore')

        # Turn this into a background task called w celery Interface    
            async def callBackgroungEntry():
                url =  'http://localhost:5000/HpClockifyApi/task/Entry'
                async with httpx.AsyncClient(timeout=300) as client:
                    await client.post(url=url, data=inputData)
            # async def callBackgroungExpense():
            #     url =  'http://localhost:5000/HpClockifyApi/task/Expense'
            #     async with httpx.AsyncClient(timeout=300) as client:
            #         await client.post(url=url, data=inputData)

            async def createTask(): # handles Entries and Expenses Once at a time
                await callBackgroungEntry()
                # await callBackgroungExpense()
                
            response = await aprocessTimesheet()
            asyncio.create_task(createTask()) # allows for Fire and Forget call of tasks  :
        
    except Exception as e:
        # transaction.rollback()
        response = JsonResponse(data= {'Message': f'{str(e)}', 'Traceback': e.__traceback__.tb_lineno}, status= status.HTTP_400_BAD_REQUEST)
        logger.error(f'Caught Exception ({e.__traceback__.tb_lineno}): {str(e)}')
        
    finally:
        logger.info('Semaphore Released')
        await saveTaskResult(response, inputData, 'UpdateTimesheet Function')
        return response


'''
Function Description: 
    Calls Client Event function to pull and update all client data from clockify to the database. 
Param: 
    request(ASGIRequest): Request sent to endpoint from client 

Returns: 
    response(Response): 
Notes: 
    Offload this to QuickBackupFunction
'''
@api_view(['POST'])
def ClientsView(request: ASGIRequest):
    secret = 'vCCa0DuhCfNnxeb3lnoXaRXE4SKcWlxi'
    secret2 = 'ITrV2e8fOhQ9nC0jXPyDXJQeZGeVtoCV'
    if not (aunthenticateRequst(request, secret) or aunthenticateRequst(request, secret2)):  
        response = JsonResponse(data={'Invalid Request': 'SECURITY ALERT'}, status=status.HTTP_423_LOCKED)
        taskResult(response, dumps(loads(request.body)), 'Client Function')
        return response
    ''' 
    Make a get method in future updates 
    if request.method == 'GET':
        clients = Client.objects.all()
        serializer = ClientSerializer(clients, many=True)
        response = Response(serializer.data )
    '''    
    if request.method != 'POST':
        response = Response(data=None, status = status.HTTP_405_METHOD_NOT_ALLOWED)
        return response
    
    logger = setup_server_logger(loggerLevel)
    stat = ClientEvent()
    logger.info(f'Client Event')
    if stat:
        return Response(data='Check logs @: https://hpclockifyapi.azurewebsites.net/', status=status.HTTP_200_OK)
    else: return Response(data='Check logs @: https://hpclockifyapi.azurewebsites.net/', status=status.HTTP_400_BAD_REQUEST)

'''
Function Description: EmployeeUsersView
    Asynchronously inserts/updates Employee's into the database. Never deletes users from the database but rather turns them to INACTIVE 
    Reads custom user fields to get the role and start date for each user. Start date must be in the form YYYY-MM-DD or exception will be raised
    If any error occurs then save the status code and optional message in the database table 'BackGroundTaskDjango'. Transactions are not 
    atomic 

Param: 
    request(ASGIRequest): Request sent to endpoint from client 

Returns: 
    response (JSONResponse): Communicates back to the client the result of the request. Usually just a string or an echo of the request 

Notes:
1. Secret Key Management: Storing API secrets directly in the code is a security risk. Instead, consider moving them to Django's settings 
 or environment variables (e.g., os.environ), which helps keep secrets out of your codebase and improves security.
2. Authentication Logic: Your authentication mechanism currently relies on checking the Clockify-Signature header against a hardcoded 
 list of secrets. Using a dictionary with descriptive keys (e.g., {'USER_JOIN_SECRET': '...', 'UPDATE_USER_SECRET': '...'}) 
  would clarify each secret’s purpose.
3. Conditional Assignment of stat: The stat variable is currently assigned based on index values. Making this more explicit, like
 mapping index to status values (e.g., a dictionary {0: 'ACTIVE', 3: 'INACTIVE'}) could improve readability.
'''
@csrf_exempt
async def EmployeeUsersView(request: ASGIRequest):
    caller = 'EmployeeUsersView '
    logger.info(caller)
    secret  = 'v9otRjmoOBTbwkf6IaBJ4VUgRGC8QU6V' # User Joined Workspace 
    secret2 = 'TSnab31ks1Ml1oXkZHMIzp7R33SRSedz' #update User 
    secret3 = 'Z9m05F1vt873wHG6hNAHok6l5YnJWmlM' # activate user 
    secret4 = 'JtyuoJ1ds3tSeXB9vyPIHjRCmb0vmmDx' #deactivate User,
    secrets = [secret, secret2, secret3, secret4]
    try: #athenticate request 
        index = secrets.index(request.headers['Clockify-Signature'])
        # decode secret to find status 
        logger.debug(index)
        if index <=2: 
            stat = 'ACTIVE'
        elif index == 3: 
            stat = 'INACTIVE'
        else: 
            raise ValueError
    except Exception:
        response = JsonResponse(data={'Invalid Request': 'SECURITY ALERT'}, status=status.HTTP_423_LOCKED)
        logger.critical(response.content)
        await saveTaskResult(response, dumps(loads(request.body)), 'User  Function')
        return response 
    if request.method != 'POST':
        response = JsonResponse(data={'Invalid Request': 'SECURITY ALERT'}, status=status.HTTP_423_LOCKED)
        await saveTaskResult(response, dumps(loads(request.body)), 'User  Function')
        return response  
     
    inputData = loads(request.body)
    inputData['status'] = stat
    logger.debug(f'\nInput Is \n {reverseForOutput(inputData)}')
    try: 
        try: 
            emp = await Employeeuser.objects.aget(id = inputData['id'])
            serializer = EmployeeUserSerializer(instance= emp, data = inputData) 
            logger.debug('Update Path taken for User ')
        except Employeeuser.DoesNotExist: 
            serializer = EmployeeUserSerializer(data=inputData)
            logger.debug('Insert Path taken for user')
        valid = await sync_to_async(serializer.is_valid)()
        if valid:
            await asave(serializer)
            logger.info(f'Saved User: {inputData['name']} ')
            response = JsonResponse(data={'User': inputData['name']}, status = status.HTTP_201_CREATED)  
            await saveTaskResult(response,inputData,caller)
        else: 
            logger.error(f'Invalid Data: {reverseForOutput(serializer.errors)}')
            raise ValidationError('Serializer could not be saved. Invalid data ')
    except Exception as e: 
            logger.info(f'({e.__traceback__.tb_lineno}) - {str(e)}')    
            response = JsonResponse(data={'Message': str(e)}, status= status.HTTP_400_BAD_REQUEST)
            asyncio.create_task(saveTaskResult(response, inputData, caller))
            return response

# impliment this function if this application is to be used over multiple workspaces. As of May 22 2024 it is not needed 
'''
@api_view(['GET', 'POST'])
def getWorkspaces(request: ASGIRequest, format = None):
    # signature = request.headers.get('X-Clockify-Signature') # or wherever the signing secret is held 
    # payload = request.body
    # secret = b'' # input signing secret here 
    # auth = hmac.compare_digest(secret,payload,hashlib.sha256).hexdigest()
    # if hmac.compare_digest(auth, signature):
        if request.method == 'GET':
            workspaces = Workspace.objects.all()
            serializer = WorkspaceSerializer(workspaces, many=True)
            response = Response(serializer.data)
        elif request.method == 'POST':
        logger = setup_server_logger(loggerLevel)    try:
                serializer = WorkspaceSerializer(data = request.data)
                if serializer.is_valid():
                    serializer.save()
                    return(Response(serializer.data, status = status.HTTP_201_CREATED))
                return ( Response( serializer.data, status = status.HTTP_400_BAD_REQUEST))
            except Exception as e:
                return (Response(data = None, status=status.HTTP_417_EXPECTATION_FAILED))
        else:
            response = Response(data=None, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    # else: 
    #     Response(data = None, status = status.HTTP_405_METHOD_NOT_ALLOWED)
   ''' 

'''
Function Description: ProjectView
    Synchronous call for the server to pull all projects and apply CRUD for all records. 

    Method is inefficient as are most of the Event functions. a Django Model/Serializer approach should be used instead to apply changes 
    only to the record passed in the request 
    
    If any error occurs then save the status code and optional message in the database table 'BackGroundTaskDjango'. Transactions are not 
    atomic 

Param: 
    request(ASGIRequest): Request sent to endpoint from client 

Returns: 
    response (JSONResponse): Communicates back to the client the result of the request. Usually just a string or an echo of the request 
Notes:
1. Log the result of the view in database using savetaskResult
'''
@csrf_exempt
async def ProjectsView(request: ASGIRequest):
    secret = 'obEJDmaQEgIrhBhLVpUO4pXO6aXgWEK3'
    logger.info(f'POST: getProjects')
    inputData = loads(request.body)
    logger.debug(reverseForOutput(inputData))
    try: 
        if not aunthenticateRequst(request, secret):  
            '''
            elif request.method == 'GET':
                projects = Project.objects.all()
                serializer = ProjectSerializer(projects, many=True)
                response = Response(serializer.data, status= status.HTTP_200_OK)
            '''
            response = JsonResponse(data={'Invalid Request': 'SECURITY ALERT'}, status=status.HTTP_423_LOCKED)
            saveTaskResult(response, dumps(loads(request.body)), 'Project Function')
            return response  
        
        if request.method != 'POST': 
            response = Response(data=None, status = status.HTTP_405_METHOD_NOT_ALLOWED)
            return response
        if inputData.get('clientId') is None or inputData.get('clientId') == '': # Projects may be created without client field. In the DB that is required
            inputData['clientId'] = '0000000000'
        try:
            project = await Project.objects.aget(pk = inputData.get('id', ''))
            serializer = ProjectSerializer(instance=project, data=inputData)
            logger.info(f'Insert path taken for Project instance')
        except Project.DoesNotExist:
            serializer = ProjectSerializer(data=inputData)
            logger.info(f'Update path taken for Project instance')
        avalid = await sync_to_async(serializer.is_valid)()
        if avalid:
            await sync_to_async (serializer.save)()
            return JsonResponse(inputData, status=status.HTTP_200_OK)
        else: 
            logger.warning(f'Serializer could not be saved: {serializer.errors}')
            for key, value in serializer.errors.items():
                logger.error(dumps({'Error Key': key, 'Error Value': value}, indent = 4))
                return JsonResponse(data= f'Failed to add project {key}: {value}', status=status.HTTP_400_BAD_REQUEST, safe = False)
    except Exception as e:
        logger.critical(f'({e.__traceback__.tb_lineno}) - {str(e)}')
        return JsonResponse(data=f'{str(e)}', status=status.HTTP_501_NOT_IMPLEMENTED, safe=False)

"""
FUNCTION: processTimeOff
Handles the creation, update, and deletion of time-off requests based on the provided HTTP method (`POST` or `DELETE`).
It interacts with the `TimeOffRequests` model in Django, and performs serialization for creating or updating records, 
and deletion when required.

Parameters:
    inputData (dict): A dictionary containing the data for the time-off request. 
                      It must include the `'id'` key, which identifies the time-off request to update or delete.
    METHOD (str, optional): Specifies the HTTP method for the operation. The default value is `'POST'`. 
                             It can be set to `'DELETE'` to delete an existing time-off request.

Logic:
    1. **POST Method**:
        - Tries to retrieve an existing `TimeOffRequests` object using the provided `id` from `inputData`.
        - If the object exists, it updates the object using the provided `inputData`.
        - If the object does not exist, it creates a new `TimeOffRequests` object with the given data.
        - Validates the serializer. If valid, it saves the object and logs the operation.
        - Returns `True` if the object is successfully saved, otherwise returns `False`.

    2. **DELETE Method**:
        - Tries to find the `TimeOffRequests` object by `id` and deletes it if it exists.
        - If the object is successfully deleted, a JSON response with a success message is returned.
        - If the object does not exist, a warning is logged, and an exception is raised.

    3. **Invalid Method**:
        - If the `METHOD` parameter is not `"POST"` or `"DELETE"`, it returns `False`.

Return Values:
    - `True`: If the time-off request is successfully saved (for `POST`).
    - `False`: If the serializer is not valid or an invalid method is provided.

Exception Handling:
    - Logs any exceptions encountered during the execution, including details about the error and its line number.

Example Usage:
    result = processTimeOff(inputData, METHOD='POST')  # To create or update a time-off request
    result = processTimeOff(inputData, METHOD='DELETE')  # To delete a time-off request

Notes:
    - Uses Django ORM for interacting with the database (`TimeOffRequests` model).
    - Serializer `TimeOffSerializer` is used for validation and saving the time-off data.
    - If any exception occurs, it logs the exception details and re-raises the error.
"""
def processTimeOff(inputData, METHOD ='POST'):
    try:
        if METHOD == "POST":
            try:
                timeoff = TimeOffRequests.objects.get(pk=inputData['id'])
                serializer = TimeOffSerializer(instance=timeoff, data = inputData)
                logger.info('Update Request Path taken')
            except TimeOffRequests.DoesNotExist:
                serializer = TimeOffSerializer(data= inputData)
            if serializer.is_valid():
                    serializer.save()
                    logger.info(f'Saved Time Off Request with id {inputData['id']}')
                    return True
            else: 
                logger.warning(f'Serializer could not be saved: {reverseForOutput(serializer.errors)} ')
                return False
        elif METHOD == 'DELETE':
            try:
                timeoff = TimeOffRequests.objects.get(id = inputData['id'])
                timeoff.delete()
                logger.info('TimeOff Request removed')
                return True
            except TimeOffRequests.DoesNotExist as e: 
                logger.warning(f'Time off request with id {inputData['id']} was not found to delete')
                raise e 
        else:
            return False
    except Exception as e:
        logger.error(f'Exception Caught  {e.__traceback__.tb_lineno}: ({str(e)})')
        raise e  
saveTimeOff = sync_to_async(processTimeOff)

'''
Function Description: TimeOffRequestsView
    Asyncrhonous CUD on timeoff requests. 

    Sometimes transient Integrity errors are raised on timesheets. Due to the try/except block which should decipher whether a update or insert is necessary
    this behaviour is unexpected. This behaviour should be reviewed and updated.
    
    If any error occurs then save the status code and optional message in the database table 'BackGroundTaskDjango'. Transactions are not 
    atomic 

Param: 
    request(ASGIRequest): Request sent to endpoint from client 

Returns: 
    response (JSONResponse): Communicates back to the client the result of the request. Usually just a string or an echo of the request 
'''
@csrf_exempt
async def TimeOffRequestsView(request: ASGIRequest):
    # One is update, one is create, either way the operation is hadled through the same path
    secret = 'W7Lc7BGRq1wvIC0eQS5Bik5m05JF8RkZ'
    secret2 = 'I7DOlIagZOjUBhHS0HObcvyaBiz7covJ'
    # one of them is to withdraw, one is to Reject. Either way we remove from database
    secret3 = 'VlEXsrENOWzsbglJZFLXZWqadeGcBcwl'
    secret4 = 'ucE6pl2renvPrqEi49KDNS1SWq8NiDld'
    method = 'POST'
    logger = setup_server_logger()
    logger.info('Approved Time Off Request function called ')
    caller = 'TimeOffRequestsView'
    if request.method == 'POST':
        response = JsonResponse(data=None, status = status.HTTP_405_METHOD_NOT_ALLOWED, safe=False)
        return response 
    if aunthenticateRequst(request, secret3) or aunthenticateRequst(request, secret4):
        method = 'DELETE'
    elif not (aunthenticateRequst(request, secret) or aunthenticateRequst(request, secret2)): 
        response = JsonResponse(data={'Invalid Request': 'SECURITY ALERT'}, status=status.HTTP_423_LOCKED)
        await saveTaskResult(response, dumps(loads(request.body)), 'TimeOff Function')
        return response 
        
    inputData = loads(request.body)
    logger.debug(f'Input is  - {reverseForOutput(inputData)}')
    try: 
        result = await saveTimeOff(inputData)
        if result: 
            response =JsonResponse(data={'Message': f'Operation Complete for Time off Request {inputData["id"]}'},
                            status=status.HTTP_201_CREATED)  # maybe include a different response for updates   
            logger.info( response.content.decode('utf-8'))
            return response
        else: 
            response = JsonResponse(data = {'Message': f'Opperation failed do to invalid Request'},
                                    status = status.HTTP_400_BAD_REQUEST)
            await saveTaskResult(response,inputData, caller)
            return response
    except Exception as e:
            logger.error(str(e))
            response = JsonResponse(data= {'Message': f'Error of type {type(e)} at {e.__traceback__.tb_lineno}'},
                                    status=status.HTTP_503_SERVICE_UNAVAILABLE)
            asyncio.create_task(saveTaskResult(response, inputData, caller))
            return response
    
#depreciated 
# Should combine this function into the quickbackup function 
@api_view(['GET', 'POST', 'PUT', 'DELETE'])
def TimeOffPoliciesView(request: ASGIRequest, format = None):
        ''' 
        elif request.method == 'GET':
            policy = Timeoffpolicies.objects.all()
            serializer = TimeOffPoliciesSerializer(policy, many=True)
            response = Response(serializer.data, status= status.HTTP_200_OK)
        '''
        if request.method == 'POST' or request.method == 'GET':
            stat = PolicyEvent()
            logger.info(f'Policy Event: Add Policy')
            if stat:
                return Response(data='Check logs @: https://hpclockifyapi.azurewebsites.net/', status=status.HTTP_200_OK)
            else: return Response(data='Check logs @: https://hpclockifyapi.azurewebsites.net/', status=status.HTTP_400_BAD_REQUEST)
        else:
            response = Response(data=None, status = status.HTTP_405_METHOD_NOT_ALLOWED)
            return response 

""" # Expense Functions no longer in use
'''
Function Description: 
    Creates/updates expense records on the database.

    FK constraint may be raised on expense categories since clockify has no way of retrieving that data first. In that case then return a 
    failed response and offload the retry logic to a secondary server at port (localhost:5000). Secondary server will then return to retry 
    the insertion/update. 
    
    If any error occurs then save the status code and optional message in the database table 'BackGroundTaskDjango'. Transactions are not 
    atomic

Param: 
    request(ASGIRequest): Request sent to endpoint from client 

Returns: 
    response (JSONResponse): Communicates back to the client the result of the request. Usually just a string or an echo of the request 
'''
@csrf_exempt
async def ExpenseView(request: ASGIRequest):
    logger = setup_server_logger(loggerLevel)
    logger.info('newExpense view called')
    secret = 'CiLrAry1UiEZb4OnPmX67T8un5GuYw24' #newExpense
    secret2 = 'l7Zqmv1BMxNPsTKKtWYEsjsHNpSfnUrj' #UpdateExpene
    try: 
        if aunthenticateRequst(request, secret) or aunthenticateRequst(request, secret2):
            inputData = loads(request.body)
            logger.debug(dumps(inputData, indent=4))
            
            if request.method == 'POST':
                def processExpense(inputData): # returns a flag for each possible FK or PK constraint raised. Only handles C flag as of May 22 2024
                    try: 
                        expenseId = create_hash(inputData['userId'], inputData['categoryId'], inputData['date'])
                        inputData['id'] = expenseId
                        serializer = ExpenseSerializer(data=inputData)
                        if serializer.is_valid():
                            serializer.save()
                            logger.info(reverseForOutput(inputData))
                            logger.info(f'Saved Expense with Id - {inputData['id']}')
                            return True
                        else:
                            for key, value in serializer.errors.items():
                                logger.error(dumps({'Error Key': key, 'Error Value': value}, indent =4))
                            raise ValidationError(serializer.errors)
                    except Exception as e: 
                        logger.error(f'Traceback {e.__traceback__.tb_lineno}: {type(e)} - {str(e)}')
                        raise e

                processExpenseAsync = sync_to_async(processExpense)
                try:
                    result = await processExpenseAsync(inputData)
                    return JsonResponse(data=inputData, status=status.HTTP_201_CREATED) 
                except ValidationError as e:
                    return JsonResponse(data={'Message': 'Invalid Input data. Review selections and try again. A simliar Expense may already exist'}, status=status.HTTP_400_BAD_REQUEST)
            
            elif request.method == 'PUT':
                def UpdateExpense(inputData): # returns a flag for each possible FK or PK constraint raised. Only handles C flag as of May 22 2024
                    try: 
                        expense = Expense.objects.get(id=inputData['id'])
                        serializer = ExpenseSerializer(data=inputData, instance=expense)
                        if serializer.is_valid():
                            serializer.save()
                            logger.info(reverseForOutput(inputData))
                            logger.info(f'Updated Expense with Id - {inputData['id']}')
                            return True
                        else:
                            for key, value in serializer.errors.items():
                                logger.error(dumps({'Error Key': key, 'Error Value': value}, indent =4))
                            raise ValidationError(serializer.errors)
                    except Expense.DoesNotExist as e:
                        logger.critical(f'input id is {inputData['id']}')
                        raise e
                    except Exception as e: 
                        logger.error(f'Traceback {e.__traceback__.tb_lineno}: {type(e)} - {str(e)}')
                        raise e

                processExpenseAsync = sync_to_async(UpdateExpense)
                try:
                    result = await processExpenseAsync(inputData)
                    return JsonResponse(data=inputData, status=status.HTTP_202_ACCEPTED) 
                except ValidationError as e:
                    return JsonResponse(data={'Message': 'Invalid Input data. Review selections and try again. A simliar Expense may already exist'}, status=status.HTTP_400_BAD_REQUEST)
            else: 
                return JsonResponse(data = None, status=status.HTTP_510_NOT_EXTENDED, safe= False)
        else:
            response = JsonResponse(data={'Invalid Request': 'SECURITY ALERT'}, status=status.HTTP_423_LOCKED)
            await saveTaskResult(response, dumps(loads(request.body)), 'NewExpense Function')
            return response
    except Exception as e: 
        response = JsonResponse(data={'Invalid Request': f'Error Occured On server ({e.__traceback__.tb_lineno}): {str(e)}'}, status=status.HTTP_501_NOT_IMPLEMENTED)
        logger.error(response.content)
        return response

@csrf_exempt
async def DeleteExpense(request: ASGIRequest):
    '''
    Function Description: 
       Deletes Expense records from the database on user request. 

       If any error occurs then save the status code and optional message in the database table 'BackGroundTaskDjango'. Transactions are not 
       atomic

    Param: 
        request(ASGIRequest): Request sent to endpoint from client 
    
    Returns: 
        response (JSONResponse): Communicates back to the client the result of the request. Usually just a string or an echo of the request 
    '''
    logger = setup_server_logger(loggerLevel)
    logger.info('Delete Expense Function called')
    secret = 'a0gfeY49Wka0HVb97DT8eYsqDo3cZIiZ'
    if aunthenticateRequst(request, secret):
        inputData = loads(request.body)
        logger.debug(f'Input data: \n{dumps(inputData, indent= 4)}')
        
        if request.method == 'POST':
            def deleteExpense():
                try:
                    expense = Expense.objects.get(id=inputData['id'], workspaceId = inputData['workspaceId'])
                    expense.delete()
                    response = JsonResponse(data = {
                        'Message': 'Expense Deleted',
                        'data': inputData
                    }, status=status.HTTP_200_OK)
                    return response
                except Expense.DoesNotExist:
                    response = JsonResponse(data=None, status= status.HTTP_204_NO_CONTENT, safe=False)
                    return response
            deleteAsync =  sync_to_async(deleteExpense)
            response = await deleteAsync()
            return response
    else:
        response = JsonResponse(data={'Invalid Request': 'SECURITY ALERT'}, status=status.HTTP_423_LOCKED)
        await saveTaskResult(response, dumps(loads(request.body)), 'DeleteExpense Function')
        return response
    
@api_view(["PUT"])
@csrf_exempt
def RequestFilesForExpense(request:ASGIRequest): 
    logger = setup_server_logger()
    logger.info('Inserting Recipt into Database for an Expense...')
    if request.method == 'PUT':
        try:
            inputData = loads(request.body)
            try: 
                file = FilesForExpense.objects.get(expenseId = inputData['expenseId'])
                serializer = FileExpenseSerializer(instance= file, data = inputData)
            except FilesForExpense.DoesNotExist as e: 
                logger.critical('Cannot find a corresponding record')
                raise FilesForExpense.DoesNotExist('Cannot Find a Corresponding record')
            if serializer.is_valid():
                logger.debug('Validated')
                serializer.save()
                logger.info(f'Opperation Complete for Expense {inputData['expenseId']}')
                logger.debug(inputData['binaryData'])
                return JsonResponse(data='SUCCSESFUL', status = status.HTTP_201_CREATED, safe= False)
            else: 
                for key, value in serializer.errors.items():
                    logger.error(dumps({'Error Key': key, 'Error Value': value}, indent =4))
                raise ValidationError(serializer.errors)
        except ValidationError as e:
            return JsonResponse(data={'Message': 'Invalid Input data. Could not serialize image'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f'Caught Exception ({e.__traceback__.tb_lineno}) - {str(e)}')
            response = JsonResponse(data={'Invalid Request': f'Error Occured On server'}, status=status.HTTP_501_NOT_IMPLEMENTED)
            taskResult(response=response, inputData=inputData, caller='requestFilesForExpense')
            return response

"""

'''
Function Description: processEntry
    Processes an entry by either updating an existing record or creating a new one if it does not exist.
Args:
    inputData (dict): A dictionary containing entry data, including 'id' and 'workspaceId'.

Process:
    - Attempts to retrieve an `Entry` based on `id` and `workspaceId`.
    - If found, initializes an `EntrySerializer` for update; otherwise, initializes for insertion.
    - Validates and saves the serializer if valid, logging success or validation errors.

Returns:
    bool: `True` if the entry is successfully processed, `False` otherwise.

Error Handling:
    - If a validation error occurs, logs each key and error message.
    - If an exception occurs, checks for foreign key constraints and logs the exact line and error message.
'''
def processEntry(inputData, METHOD = 'POST'):
    try:
        if METHOD == "POST":
            try:
                entry = Entry.objects.get(id=inputData['id'], workspaceId=inputData['workspaceId'])
                serializer = EntrySerializer(instance=entry, data= inputData )
                logger.info(f'Update path taken for Entry')
            except Entry.DoesNotExist:
                serializer = EntrySerializer(data = inputData )
                logger.info(f'Insert path taken for Entry')
            if serializer.is_valid():
                serializer.save()
                logger.info('\tOperation Complete')
                
                return True
            else:
                logger.warning(f'Serializer could not be saved: {serializer.errors}')
                for key, value in serializer.errors.items():
                    # Print the key and each error code and message
                    logger.error(dumps({'Error Key': key, 'Error Value': value}, indent = 4))
                        
                return False # Unknown, Raise error (BAD Request)
        if METHOD == "DELETE":
            try:
                expense = Entry.objects.get(id=inputData['id'], workspaceId = inputData['workspaceId'])
                expense.delete()
                logger.info('Entry Deleted...')
                return True
            except Entry.DoesNotExist:
                logger.warning('Entry was not deleted successfully')
                return False
        else: 
            return False
    except Exception as e:
        '''
        include check for other foreign keys to know which foreign key 
        constraint is violated and which function should handle it
        '''
        logger.error(f'Exception Caught  {e.__traceback__.tb_lineno}: ({str(e)})')
        raise e
processEntryAsync = sync_to_async(processEntry)
entrySemaphore = asyncio.Semaphore(1)

'''
Function Description: EntryView
    Creates/updates/Deletes entry records on the database. Includes robust logging on database exceptions
    
    Observed one exception where entry request has null duration which should not be allowed. Investigation into why/how this happend is 
    needed. 

    If any error occurs then save the status code and optional message in the database table 'BackGroundTaskDjango'. Transactions are not 
    atomic

Param: 
    request(ASGIRequest): Request sent to endpoint from client 

Returns: 
    response (JSONResponse): Communicates back to the client the result of the request. Usually just a string or an echo of the request 
'''
@csrf_exempt
async def EntryView(request:ASGIRequest):
    caller = 'New Entry view called'
    logger = setup_server_logger()
    logger.debug(request.headers)
    logger.info(caller)
    secret = 'e2kRQ3xauRrfFqkyBMsgRaCLFagJqmCE' #newEntry 
    secret2 = 'Ps4GN6oxDKYh9Q33F1BULtCI7rcgxqXW' #updateEntry 
    secret3 = '0IQNBiGEAejNMlFmdQc8NWEiMe1Uzg01' #DeleteEntry  
    method = 'POST'
    retryFlag = True
    maxRetries = 3
    retryCount = 0
    while retryFlag and maxRetries > retryCount:
        if retryCount > 0: 
            logger.info('\tRetrying....')
        retryCount += 1
        retryFlag = False
        try:
            if aunthenticateRequst(request, secret3):
                method = 'DELETE'
            elif not (aunthenticateRequst(request, secret) or aunthenticateRequst(request, secret2)):
                response = JsonResponse(data={'Invalid Request': 'SECURITY ALERT'}, status=status.HTTP_423_LOCKED)
                asyncio.create_task(saveTaskResult(response, inputData, caller))
                break

            #Get input Data 
            try:
                inputData = loads(request.body)
            except Exception:
                logger.warning('Unknown Exception, attempting to handle')
                inputData = request.POST

            #assert POST
            if request.method != 'POST':
                response = JsonResponse(data={'Inalid Method': request.method}, status=status.HTTP_405_METHOD_NOT_ALLOWED, safe= False)
                asyncio.create_task(saveTaskResult(response, inputData, caller))
                break

            logger.info('\tWaiting for Entry Semaphore')
            async with entrySemaphore: # only 3 concurent tasks
                logger.info('\tEntry Semaphore Aquired')
                # store data
                logger.debug(reverseForOutput(inputData))
                result = await processEntryAsync(inputData, method)
            logger.info('Entry Semaphore Released')
            
            # generate response
            if result:
                response = JsonResponse(data=inputData, status=status.HTTP_202_ACCEPTED)
                break
            response =  JsonResponse(
                data= {
                    'Message': 'Post Data could not be validated. Review Logs'
                    },
                    status=status.HTTP_400_BAD_REQUEST
            )    
            break

        except Exception as e: 
            response = JsonResponse(data= {'Message': f'({e.__traceback__.tb_lineno}): {str(e)}'}, status= status.HTTP_503_SERVICE_UNAVAILABLE)
            logger.error(f"({e.__traceback__.tb_lineno}) - {str(e)}")
            if 'deadlocked' in str(e):
                retryFlag = await pauseOnDeadlock('newEntry', inputData.get('id', ''))
            else:
                break
    if maxRetries <= retryCount:
        response = JsonResponse(data={'Message': 'Failed to process request after multiple attempts.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    asyncio.create_task(saveTaskResult(response, inputData, caller))
    return response
 
'''
Function Description: Quick Backup 
    Calls every Clockify pull and Push Event syncrhonsously. takes Approx 10 min.

    In a future version, impliment the data pull for non sync attribute ( policies, Holidays, files/reciepts) through this endpoint. 
    this will maintain data integrity on a more specific scale to avoid any possible FK constraints 
    
Param: 
    request(ASGIRequest): Request sent to endpoint from client 

Returns: 
    response(Response)
'''
@csrf_exempt
async def QuickBackup(request: ASGIRequest = None, event = None):
    try:
        result = await eventSelect(event)
        response = JsonResponse(data = result, status=status.HTTP_200_OK, safe=False)
    except Exception as e:
        logger.error(f'Quickbackup: {e.__traceback__.tb_lineno} {str(e)}')
        response = JsonResponse(data = str(e), status=status.HTTP_207_MULTI_STATUS, safe=False)
    finally: 
        return response or JsonResponse(data = 'An Error Occured', status = status.HTTP_500_INTERNAL_SERVER_ERROR)
    
@api_view(['GET', 'POST'])
# @csrf_exempt
def BankedHrs(request: ASGIRequest):
    '''
    Function Description: 
        Calls pull request functions from the databse to update the banked hours ballance in clockify. 
    Param: 
        request(ASGIRequest): Request sent to endpoint from client 
    
    Returns: 
        response(Response): contains Payroll Report File to be directly uploaded into ACC
    '''
    logger.info(f'{request.method}: bankedHours ')
    try:
        BankedTime()
        return JsonResponse(data='Operation Completed', status=status.HTTP_200_OK, safe=False)
    except Exception as e:
        logger.error(f'{str(e)}')
        return JsonResponse(data='Error: Check Logs @ https://hpclockifyapi.azurewebsites.net/', status=status.HTTP_503_SERVICE_UNAVAILABLE, safe=False)

@api_view(['GET', 'POST'])
# @csrf_exempt
def UpdateSalaryVacation(request: ASGIRequest):
    '''
    Function Description: 
        Calls pull request functions from the databse to update the vacation hours ballance in clockify. 
    Param: 
        request(ASGIRequest): Request sent to endpoint from client 
    
    Returns: 
        response(Response): contains Payroll Report File to be directly uploaded into ACC
    '''
    logger.info(f'{request.method}: bankedHours ')
    try:
        cursor, conn = sqlConnect()
        users = list(Employeeuser.objects.filter(hourly = 0) )
        for usr in users:
            updateSalaryVacation(usr, cursor)
        cleanUp(conn, cursor)
        return JsonResponse(data='Operation Completed', status=status.HTTP_200_OK, safe=False)
    except Exception as e:
        logger.error(f'{str(e)}')
        return JsonResponse(data='Error: Check Logs @ https://hpclockifyapi.azurewebsites.net/', status=status.HTTP_503_SERVICE_UNAVAILABLE, safe=False)

