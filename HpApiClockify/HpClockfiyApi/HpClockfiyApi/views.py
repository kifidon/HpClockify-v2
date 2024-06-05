'''
PERFORMANCE CONSIDERATIONS 

More consistent error logging scheme needs to be done. Code should be cleaned up so that the logic is more consistent accross similar opperations.
Currently some of the functions use slightly different logging messages and flag diffferent operations as INFO/DEBUG/ERROR which may cause confusion 
when debugging and error handling.

Besides the Update approval and new Expense functions, no retry logic has been put into place for FK or PK constraints. A simple solution is to 
return a result to the client, offload the constraint handling to secondary server/port, and then resubmit the request to the endpoint. Include
a flag so infinite loops do not occur.

csrf_exempt on async functions is not secure. Should be implimented in a future version and decorated using @api_view as for sycnchronous methods.
The secondary server rouritng system is feture complemete but should be switched out instead to use celery with raddis or rabbitmq message brokers 
for better logging and completion of background tasks. 

ASGI server deployment needs to be optimized for scaling. I noticed when 10+ requests are sent to specifically the approvalUpdate function at once
(User pressed the Approval All button on clockify) some data may get lost or transient errors arrise.

Clockify sends all requests as POST thus seprate views are used to handle different methods
'''

from django.http import JsonResponse, HttpResponse
from django.core.handlers.asgi import ASGIRequest
from rest_framework.exceptions import ErrorDetail
from rest_framework.decorators import api_view
from django.views.decorators.csrf import csrf_exempt
from django.db import  utils  #, transaction
from .serializers import (
    EmployeeUserSerializer,
    FileExpenseSerializer,
    TimesheetSerializer,
    TimeOffSerializer,
    ExpenseSerializer,
    EntrySerializer,

)
from .models import(
    TimeOffRequests,
    FilesForExpense,
    Employeeuser,
    Timesheet,
    Expense,
    Entry,
)
from asgiref.sync import sync_to_async
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response 
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
import os
from .clockify_util.QuickBackupV3 import main, TimesheetEvent, monthlyBillable, weeklyPayroll, ClientEvent, ProjectEvent,  PolicyEvent
from .clockify_util import SqlClockPull
from .clockify_util.hpUtil import asyncio, taskResult, dumps, loads, reverseForOutput, download_text_file, create_hash
from . Loggers import setup_server_logger
from . import settings

from json.decoder import JSONDecodeError
import httpx
import base64

loggerLevel = 'DEBUG'
logger = setup_server_logger(loggerLevel)
saveTaskResult = sync_to_async(taskResult, thread_sensitive=True)

def aunthenticateRequst(request: ASGIRequest, secret: str): 
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
    logger.info('Validating Request...')
    signature = request.headers.get('Clockify-Signature') 
    logger.debug(signature)
    if secret == signature:
        logger.info('Request Validated!')
        return True
    else: 
        logger.debug('Invalid Request')
        return False

@csrf_exempt
async def updateTimesheets(request:ASGIRequest):
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
    secret = 'me1lD8vSd5jqmBeaO2DpZvtQ2Qbwzrmy'
    if aunthenticateRequst(request, secret):
        if request.method == 'POST':
            logger = setup_server_logger(loggerLevel)
            logger.info(f'{request.method}: updateTimesheet')
            try: 
                inputData = loads(request.body)
                def updateApproval(): # create thread 
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
                            # task = asyncio.ensure_future(updateEntries(request, serializer))
                            # await asyncio.wait([task])
                            response = JsonResponse(data={
                                                    'timesheet':serializer.validated_data
                                                }, status = status.HTTP_202_ACCEPTED)
                            logger.info(f'UpdateTimesheet:{dumps(inputData["id"])}{response.status_code}')
                            return [response, serializer]
                        else: 
                            response = JsonResponse(data=serializer.error_messages, status=status.HTTP_400_BAD_REQUEST)
                            logger.error(f'UpdateTimesheet:{dumps(inputData["id"])}{response.status_code}')
                            return [response, None]
                    except Exception as e: 
                        logger.error(f'Unknown error ({e.__traceback__.tb_lineno}): {str(e)}')
                        raise e

                async def callBackgroungEntry():
                    url =  'http://localhost:5000/HpClockifyApi/task/Entry'
                    async with httpx.AsyncClient(timeout=300) as client:
                        await client.post(url=url, data=inputData)
                async def callBackgroungExpense():
                    url =  'http://localhost:5000/HpClockifyApi/task/Expense'
                    async with httpx.AsyncClient(timeout=300) as client:
                        await client.post(url=url, data=inputData)

                async def createTask(): # handles Entries and Expenses Once at a time
                    await callBackgroungEntry()
                    # await callBackgroungExpense()
                    
                updateAsync = sync_to_async(updateApproval, thread_sensitive=True)
                result = await updateAsync()
                if result[1]: 
                    asyncio.create_task(createTask()) # allows for Fire and Forget call of tasks  
                else: 
                    raise ValidationError('Unknown Error occured. Timesheet Serializer not created.')
                return result[0]
            except Exception as e:
                # transaction.rollback()
                response = JsonResponse(data= {'Message': f'{str(e)}', 'Traceback': e.__traceback__.tb_lineno}, status= status.HTTP_400_BAD_REQUEST)
                await saveTaskResult(response, inputData, 'UpdateTimesheet Function')
                logger.error(f'Caught Exception ({e.__traceback__.tb_lineno}): {str(e)}')
                return response
        else:
            response = JsonResponse(data={'Message': f'Method {request.method} not allowed'}, status = status.HTTP_405_METHOD_NOT_ALLOWED)
            await saveTaskResult(response, dumps(loads(request.body)), 'UpdateTimesheet Function')
            return response
    else:
        response = JsonResponse(data={'Invalid Request': 'SECURITY ALERT'}, status=status.HTTP_423_LOCKED)
        await saveTaskResult(response, dumps(loads(request.body)), 'UpdateTimesheet Function')
        return response

@api_view(['POST'])
def newTimeSheets(request: ASGIRequest):
    '''
    Function Description: 
        Syncrhonosuly inserts a timesheet as a pending approval request. Does not search for entries or Expenses yet. In a future version move the entry/expense
        functions to this function (since new timesheets happen 1 at a time and updates can be done in batches) in conjuction with the newEntry and 
        newExpense function for better data management.

        If any error occurs then save the status code and optional message in the database table 'BackGroundTaskDjango'. Transactions are not atomic 

    Param: 
        request(ASGIRequest): Request sent to endpoint from client 
    
    Returns: 
        response (JSONResponse): Communicates back to the client the result of the request. Usually just a string or an echo of the request 
    '''
    logger = setup_server_logger(loggerLevel)
    logger.info(f'{request.method}: newTimesheet')
    secret = 'Qzotb4tVT5QRlXc3HUjwZmkgIk58uUyK'
    if aunthenticateRequst(request, secret):
        if request.method == 'POST':
            logger = setup_server_logger(loggerLevel)
            try:
                data = loads(request.body)
                serializer = TimesheetSerializer(data= data)
                if serializer.is_valid():
                    serializer.save()
                    response = JsonResponse(data={'timesheet':serializer.validated_data} ,status=status.HTTP_201_CREATED)
                    logger.info(f'NewTimesheet:{dumps(data["id"])}{response.status_code}')
                    return response
                else:
                    response = Response(data= serializer.error_messages, status=status.HTTP_400_BAD_REQUEST)
                    logger.error(f'{response}')
                    return response
            except utils.IntegrityError as e:
                if 'PRIMARY KEY constraint' in str(e): 
                    response = JsonResponse(data={'Message': f'Cannot create new Timesheet because id {request.data["id"]} already exists'}, status=status.HTTP_409_CONFLICT, safe=False)
                    logger.error(f'Cannot create new Timesheet because id {request.data["id"]} already exists')
                    taskResult(response, data, 'New Timesheet Function')
                    return response
                elif('FOREIGN KEY') in str(e): # maybe include calls to update and try again in the future 
                    response = JsonResponse(data={'Message': f'Cannot create new Timesheet data includes Foregin Constraint Violation'}, status=status.HTTP_406_NOT_ACCEPTABLE, safe=False)
                    logger.error(response.content)
                    taskResult(response, data, 'New Timesheet Function')
                    return response
                else:
                    response = Response(data=str(e), status = status.HTTP_400_BAD_REQUEST) 
                    logger.error(f"on timesheet {request.data['id']}")
                    logger.error(f'{response}')
                    return response
            except Exception as e:
                logger.error(f"On timesheet {request.data['id']}: {str(e)} at {e.__traceback__.tb_lineno}")
                response = JsonResponse(data=str(e), status=status.HTTP_503_SERVICE_UNAVAILABLE, safe= False)
                taskResult(response, data, 'New Timesheet Function')
                return response
        else:
            response = Response(data=None, status = status.HTTP_405_METHOD_NOT_ALLOWED)
            return response
    else:
        response = JsonResponse(data={'Invalid Request': 'SECURITY ALERT'}, status=status.HTTP_423_LOCKED)
        taskResult(response, dumps(loads(request.body)), 'NewTimesheet Function')
        return response

#depreciated 
@csrf_exempt
async def quickBackup(request: ASGIRequest):
    '''
    Function Description: 
        Calls every Clockify pull and Push Event syncrhonsously. takes Approx 10 min.

        In a future version, impliment the data pull for non sync attribute ( policies, Holidays, files/reciepts) through this endpoint. 
        this will maintain data integrity on a more specific scale to avoid any possible FK constraints 
        
    Param: 
        request(ASGIRequest): Request sent to endpoint from client 
    
    Returns: 
        response(Response)
    '''
    try: 
        result = await main() # General String for return output
    except Exception as e:
        logger.info(f'Quickbackup:  {response.data}, {response.status_code}')
    finally: 
        response = JsonResponse(data = result, status=status.HTTP_200_OK, safe=False)
        return response

#depreciated
@api_view(['GET'])
def timesheets(request: ASGIRequest):
    '''
    Function Description: 
       Pulls all timesheets from Clockify and updates/inserts them into the database. Also check for insert/updates on Time Entries in the same iteration.
       Performance is slow and takes approx (10 min).

       In future versions change the clockify pull api request to sort-by=UPDATED_AT to only iterate through ~= 54 ( number of timesheets per week)
       recently updated timesheets instead of all 1000+
    Param: 
        request(ASGIRequest): Request sent to endpoint from client 
    
    Returns: 
        response(Response)
    '''
    result = TimesheetEvent(status='APPROVED')
    response = Response(data = result, status=status.HTTP_200_OK)
    logger.info(f'Quickbackup:  {response.data}, {response.status_code}')
    
    return response


@api_view(['GET'])
def monthlyBillableReport(request, start_date = None, end_date= None):
    '''
    Function Description: 
       Calls format function to build the billing report based on the information in the database. Default values when no start and end date is given 
       are taken as the current month. Otherwise start_date and end_date are specified in the URL in the YYYY-MM-DD format.

       In future versions create a form web submission where the start date and end date can be passed as input and not part of the endpoint url 
    Param: 
        request(ASGIRequest): Request sent to endpoint from client 
    
    Returns: 
        response(Response): contains Billable Report File to be directly uploaded into ACC
    '''
    logger = setup_server_logger(loggerLevel)
    logger.info('BillableReport Called')
    folder_path = monthlyBillable(start_date, end_date )
    return download_text_file(folder_path)

@api_view(['GET'])
def weeklyPayrollReport(request, start_date=None, end_date= None):
    '''
    Function Description: 
       Calls format function to build the payroll report based on the information in the database. Default values when no start and end date is given 
       are taken as the current month. Otherwise start_date and end_date are specified in the URL in the YYYY-MM-DD format.

       In future versions create a form web submission where the start date and end date can be passed as input and not part of the endpoint url 
    Param: 
        request(ASGIRequest): Request sent to endpoint from client 
    
    Returns: 
        response(Response): contains Payroll Report File to be directly uploaded into ACC
    '''
    logger = setup_server_logger()
    logger.info(f'Weekly Payroll Report Called')
    folder_path = weeklyPayroll(start_date, end_date )
    return download_text_file(folder_path)

@api_view(['GET'])
def viewServerLog(request):
    '''
    Function Description: 
       Displays Server log file through the browser.

       In future versions impliment a submission form to have the user log in. This data should not be completly public as it contains all the data passed 
       to the database 
    Param: 
        request(ASGIRequest): Request sent to endpoint from client 
    
    Returns: 
        response(Response): 
    '''
    log_file_path = os.path.join(settings.LOGS_DIR, 'ServerLog.log')  # Update with the path to your logger file
    if os.path.exists(log_file_path):
        with open(log_file_path, 'r') as file:
            # Read all lines from the file
            lines = file.readlines()
            # Extract the last 1000 lines
            last_1000_lines = lines[-5000:]
            # Reverse the order of the lines
            reversed_lines = reversed(last_1000_lines)
            # Join the lines into a single string
            log_contents = ''.join(reversed_lines)
        return HttpResponse(log_contents, content_type='application/json')
    else:
        return HttpResponse('logger file not found', status=404)

@api_view(['GET'])
def viewTaskLog(request):
    '''
    Function Description: 
       Displays Server log file through the browser.

       In future versions impliment a submission form to have the user log in. This data should not be completly public as it contains all the data passed 
       to the database 
    Param: 
        request(ASGIRequest): Request sent to endpoint from client 
    
    Returns: 
        response(Response): 
    '''
    log_file_path = os.path.join(settings.LOGS_DIR, 'BackgroundTasksLog.log')  # Update with the path to your logger file
    if os.path.exists(log_file_path):
        with open(log_file_path, 'r') as file:
            # Read all lines from the file
            lines = file.readlines()
            # Extract the last 1000 lines
            last_1000_lines = lines[-5000:]
            # Reverse the order of the lines
            reversed_lines = reversed(last_1000_lines)
            # Join the lines into a single string
            log_contents = ''.join(reversed_lines)
        return HttpResponse(log_contents, content_type='application/json')
    else:
        return HttpResponse('logger file not found', status=404)
    
@api_view(['GET', 'POST'])
def bankedHrs(request: ASGIRequest):
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
        SqlClockPull.main()
        return Response(data='Operation Completed', status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f'{str(e)}')
        return Response(data='Error: Check Logs @ https://hpclockifyapi.azurewebsites.net/', status=status.HTTP_406_NOT_ACCEPTABLE)

@api_view(['POST'])
def getClients(request: ASGIRequest):
    '''
    Function Description: 
        Calls Client Event function to pull and update all client data from clockify to the database. 
    Param: 
        request(ASGIRequest): Request sent to endpoint from client 
    
    Returns: 
        response(Response): 
    '''
    secret = 'vCCa0DuhCfNnxeb3lnoXaRXE4SKcWlxi'
    secret2 = 'ITrV2e8fOhQ9nC0jXPyDXJQeZGeVtoCV'
    if aunthenticateRequst(request, secret) or aunthenticateRequst(request, secret2):  
        ''' 
        Make a get method in future updates 
        if request.method == 'GET':
            clients = Client.objects.all()
            serializer = ClientSerializer(clients, many=True)
            response = Response(serializer.data )
        '''    
        if request.method == 'POST':
            logger = setup_server_logger(loggerLevel)
            stat = ClientEvent()
            logger.info(f'Client Event: Add Client')
            if stat:
                return Response(data='Check logs @: https://hpclockifyapi.azurewebsites.net/', status=status.HTTP_200_OK)
            else: return Response(data='Check logs @: https://hpclockifyapi.azurewebsites.net/', status=status.HTTP_400_BAD_REQUEST)
        else:
            response = Response(data=None, status = status.HTTP_405_METHOD_NOT_ALLOWED)
            return response
    else:
        response = JsonResponse(data={'Invalid Request': 'SECURITY ALERT'}, status=status.HTTP_423_LOCKED)
        taskResult(response, dumps(loads(request.body)), 'Client Function')
        return response

@csrf_exempt
async def getEmployeeUsers(request: ASGIRequest):
    '''
    Function Description: 
        Asynchronously inserts/updates Employee's into the database. Never deletes users from the database but rather turns them to INACTIVE 

        Reads custom user fields to get the role and start date for each user. Start date must be in the form YYYY-MM-DD or exception will be raised 

        If any error occurs then save the status code and optional message in the database table 'BackGroundTaskDjango'. Transactions are not 
        atomic 

    Param: 
        request(ASGIRequest): Request sent to endpoint from client 
    
    Returns: 
        response (JSONResponse): Communicates back to the client the result of the request. Usually just a string or an echo of the request 
    '''
    caller = 'EmployeeUser Function '
    logger.info(caller)
    secret  = 'v9otRjmoOBTbwkf6IaBJ4VUgRGC8QU6V' # User Joined Workspace 
    secret2 = 'TSnab31ks1Ml1oXkZHMIzp7R33SRSedz' #update User 
    secret3 = 'Z9m05F1vt873wHG6hNAHok6l5YnJWmlM' # activate user 
    secret4 = 'JtyuoJ1ds3tSeXB9vyPIHjRCmb0vmmDx' #deactivate User,
    secrets = [secret, secret2, secret3, secret4]
    try: #athenticate request 
        index = secrets.index(request.headers['Clockify-Signature'])
        # decode secret to find status 
        if index <=2: 
            stat = 'ACTIVE'
        if index == 3: 
            stat = 'INACTIVE'
    except ValueError:
        response = JsonResponse(data={'Invalid Request': 'SECURITY ALERT'}, status=status.HTTP_423_LOCKED)
        logger.critical(response.content)
        saveTaskResult(response, dumps(loads(request.body)), 'User  Function')
        return response 

    if request.method == 'POST': 
        inputData = loads(request.body)
        logger.debug(f'\nInput Is \n {reverseForOutput(inputData)}')
        def updateSync(inputData):
            try: 
                try: 
                    emp = Employeeuser.objects.get(id = inputData['id'])
                    serializer = EmployeeUserSerializer(instance= emp, data = inputData, context = {'status': stat}) # change later 
                    logger.debug('Update Path taken for User ')
                except Employeeuser.DoesNotExist: 
                    serializer = EmployeeUserSerializer(data=inputData)
                    logger.debug('Insert Path taken for user ')

                if serializer.is_valid():
                    serializer.save()
                    logger.info(f'Saved User: {inputData['name']} ')
                    return True 
                else: 
                    logger.error(f'Invalid Data: {reverseForOutput(serializer.errors)}')
                    raise ValidationError('Serializer could not be saved. Invalid data ')
            except Exception as e: 
                if not isinstance(e, ValidationError): 
                    logger.error(f'Unknown Error ({e.__traceback__.tb_lineno}) {str(e)}')
                    raise e
                raise e

        saveUser = sync_to_async(updateSync)
        try: 
            result = await saveUser(inputData)   
            if result: 
                return JsonResponse(data={'User': inputData['name']}, status = status.HTTP_201_CREATED)  
            else: raise Exception('Unknown Behavior ')   
        except Exception as e: 
            logger.info(f'({e.__traceback__.tb_lineno}) - {str(e)}')    
            response = JsonResponse(data={'Message': str(e)}, status= status.HTTP_400_BAD_REQUEST)
            asyncio.create_task(saveTaskResult(response, inputData, caller))
            return response
    else: 
        response = JsonResponse(data={'Invalid Request': 'SECURITY ALERT'}, status=status.HTTP_423_LOCKED)
        saveTaskResult(response, dumps(loads(request.body)), 'User  Function')
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

@api_view(['GET', 'POST',])
def getProjects(request: ASGIRequest):
    '''
    Function Description: 
        Synchronous call for the server to pull all projects and apply CRUD for all records. 

        Method is inefficient as are most of the Event functions. a Django Model/Serializer approach should be used instead to apply changes 
        only to the record passed in the request 
        
        If any error occurs then save the status code and optional message in the database table 'BackGroundTaskDjango'. Transactions are not 
        atomic 

    Param: 
        request(ASGIRequest): Request sent to endpoint from client 
    
    Returns: 
        response (JSONResponse): Communicates back to the client the result of the request. Usually just a string or an echo of the request 
    '''
    secret = 'obEJDmaQEgIrhBhLVpUO4pXO6aXgWEK3'
    logger.info(f'POST: getProjects')
    if aunthenticateRequst(request, secret):  
        '''
        elif request.method == 'GET':
            projects = Project.objects.all()
            serializer = ProjectSerializer(projects, many=True)
            response = Response(serializer.data, status= status.HTTP_200_OK)
        '''
        if request.method == 'POST' or request.method=='GET': 
            stat = ProjectEvent()
            logger.info(f'Project Event ')
            if stat:
                return Response(data= 'Check logs @: https://hpclockifyapi.azurewebsites.net/', status=status.HTTP_200_OK)
            else: return Response(data='Check logs @: https://hpclockifyapi.azurewebsites.net/', status=status.HTTP_400_BAD_REQUEST)
        else:
            response = Response(data=None, status = status.HTTP_405_METHOD_NOT_ALLOWED)
            return response
    else:
        response = JsonResponse(data={'Invalid Request': 'SECURITY ALERT'}, status=status.HTTP_423_LOCKED)
        taskResult(response, dumps(loads(request.body)), 'Project Function')
        return response  

@csrf_exempt
async def getTimeOffRequests(request: ASGIRequest):
    '''
    Function Description: 
        Asyncrhonous CU on timeoff requests. 

        Sometimes transient Integrity errors are raised on timesheets. Due to the try/except block which should decipher whether a update or insert is necessary
        this behaviour is unexpected. This behaviour should be reviewed and updated.
        yet to develop a method for confirming the data in the databse is consistent with that in clockify. Since implimentation of this function,
        switching from an Event algorithm on May 22 2024 data should be in better aggreement. A database audit for time off requests is needed.

        If any error occurs then save the status code and optional message in the database table 'BackGroundTaskDjango'. Transactions are not 
        atomic 

    Param: 
        request(ASGIRequest): Request sent to endpoint from client 
    
    Returns: 
        response (JSONResponse): Communicates back to the client the result of the request. Usually just a string or an echo of the request 
    '''
    secret = 'W7Lc7BGRq1wvIC0eQS5Bik5m05JF8RkZ'
    secret2 = 'I7DOlIagZOjUBhHS0HObcvyaBiz7covJ'
    logger = setup_server_logger()
    logger.info('Approved Time Off Request function called ')
    caller = 'getTimeOffRequests'
    if aunthenticateRequst(request, secret) or aunthenticateRequst(request, secret2): 
        if request.method == 'POST':
            inputData = loads(request.body)
            logger.debug(f'Input is  - {reverseForOutput(inputData)}')
            
            def updateSync(inputData):
                try:
                    # logger = setup_server_logger()
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
                except Exception as e:
                    logger.error(f'Exception Caught  {e.__traceback__.tb_lineno}: ({str(e)})')
                    raise e
            saveTimeOff = sync_to_async(updateSync)
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
        else:
            response = JsonResponse(data=None, status = status.HTTP_405_METHOD_NOT_ALLOWED, safe=False)
            return response
    else:
        response = JsonResponse(data={'Invalid Request': 'SECURITY ALERT'}, status=status.HTTP_423_LOCKED)
        await saveTaskResult(response, dumps(loads(request.body)), 'TimeOff Function')
        return response  

@csrf_exempt
async def removeTimeOffRequests(request:ASGIRequest):
    '''
    Function Description: 
       Asynchronous removal of TimeoffRequests whenever they are rejected or withdrawn.
       
       If any error occurs then save the status code and optional message in the database table 'BackGroundTaskDjango'. Transactions are not 
       atomic

    Param: 
        request(ASGIRequest): Request sent to endpoint from client 
    
    Returns: 
        response (JSONResponse): Communicates back to the client the result of the request. Usually just a string or an echo of the request 
    '''
    secret = 'VlEXsrENOWzsbglJZFLXZWqadeGcBcwl'
    secret2 = 'ucE6pl2renvPrqEi49KDNS1SWq8NiDld'
    if aunthenticateRequst(request, secret) or aunthenticateRequst(request, secret2):
        if request.method == 'POST':
            try:
                inputData = loads(request.body)
                def deleteTime(inputData):
                    try:
                        timeoff = TimeOffRequests.objects.get(id = inputData['id'])
                        timeoff.delete()
                        logger.info('TimeOff Request removed')
                        return True 
                    except TimeOffRequests.DoesNotExist as e: 
                        logger.warning(f'Time off request with id {inputData['id']} was not found to delete')
                        raise e 
                
                remove = sync_to_async(deleteTime)
                await remove(inputData)
                return JsonResponse(data= {'Message': f'Deleted Time off request {inputData['id']}'}, status = status.HTTP_200_OK)
            except Exception as e: 
                response = JsonResponse(data= {'Message': f'({e.__traceback__.tb_lineno}): {str(e)}'})
                logger.error(response.content)
                await saveTaskResult(response, dumps(loads(request.body)), 'TimeOff delete Function')
                return response  
        else: 
            response = JsonResponse(data={'Message': f'Method {request.method} not allowed'}, status = status.HTTP_405_METHOD_NOT_ALLOWED)
            await saveTaskResult(response, dumps(loads(request.body)), 'UpdateTimesheet Function')
            return response
    else:
        response = JsonResponse(data={'Invalid Request': 'SECURITY ALERT'}, status=status.HTTP_423_LOCKED)
        await saveTaskResult(response, dumps(loads(request.body)), 'TimeOff Function')
        return response
    
#depreciated 
# Should combine this function into the quickbackup function 
@api_view(['GET', 'POST', 'PUT', 'DELETE'])
def getTimeOffPolicies(request: ASGIRequest, format = None):
 
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

@csrf_exempt
async def newExpense(request: ASGIRequest):
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
                                logger.info(dumps({'Error Key': key, 'Error Value': value}, indent =4))
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
                                logger.info(dumps({'Error Key': key, 'Error Value': value}, indent =4))
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
async def newEntry(request:ASGIRequest):
    '''
    Function Description: 
       Creates/updates entry records on the database. Includes robust logging on database exceptions
       
       Observed one exception where entry request has null duration which should not be allowed. Investigation into why/how this happend is 
       needed. 

       If any error occurs then save the status code and optional message in the database table 'BackGroundTaskDjango'. Transactions are not 
       atomic

    Param: 
        request(ASGIRequest): Request sent to endpoint from client 
    
    Returns: 
        response (JSONResponse): Communicates back to the client the result of the request. Usually just a string or an echo of the request 
    '''
    caller = 'New Entry view called'
    logger = setup_server_logger()
    logger.debug(request.headers)
    logger.info(caller)
    secret = 'e2kRQ3xauRrfFqkyBMsgRaCLFagJqmCE' #newEntry 
    secret2 = 'Ps4GN6oxDKYh9Q33F1BULtCI7rcgxqXW' #updateEntry  
    try:
        if aunthenticateRequst(request, secret) or aunthenticateRequst(request, secret2):
            if request.method == 'POST':
                try:
                    inputData = loads(request.body)
                    RetryFlag = False 
                except Exception:
                    logger.warning('Unknown Exception, attempting to handle')
                    inputData = request.POST
                    RetryFlag = True
                logger.debug(reverseForOutput(inputData))

                def processEntry(inputData):
                    try:
                        entry = Entry.objects.get(id=inputData['id'], workspaceId=inputData['workspaceId'])
                        serializer = EntrySerializer(instance=entry, data= inputData )
                        logger.info(f'Update path taken for Entry')
                    except Entry.DoesNotExist:
                        serializer = EntrySerializer(data = inputData )
                        logger.info(f'Insert path taken for Entry')
                    if serializer.is_valid():
                        serializer.save()
                        # do the rest 
                        return True, 'V'
                    else:
                        #force backgroung task 
                        logger.warning(f'Serializer could not be saved: {serializer.errors}')
                        for key, value in serializer.errors.items():
                            logger.info(dumps({'Error Key': key, 'Error Value': value}, indent = 4))
                            # Check if the value is an instance of ErrorDetail
                            if isinstance(value, list) and all(isinstance(item, ErrorDetail) for item in value):
                                # Print the key and each error code and message
                                for error_detail in value:
                                    code = error_detail.code
                                    field = key
                                    '''
                                    include check for other foreign keys to know which foreign key 
                                    constraint is violated and which function should handle it
                                    '''
                                    if code == 'does_not_exist': 
                                        return False, 'C' # C for category P for Project, F for file in later updates 
                        return False, 'X' # Unknown, Raise error (BAD Request)
                
                processEntryAsync = sync_to_async(processEntry)
                result = await processEntryAsync(inputData)
                if result[0]:
                    return JsonResponse(data=inputData, status=status.HTTP_202_ACCEPTED)
                else:
                    return JsonResponse(
                        data= {
                            'Message': 'Post Data could not be validated. Review Logs'
                            },
                            status=status.HTTP_400_BAD_REQUEST
                    )
        else:
            response = JsonResponse(data={'Invalid Request': 'SECURITY ALERT'}, status=status.HTTP_423_LOCKED)
            await saveTaskResult(response, dumps(loads(request.body)), 'NewEntry Function')
            return response
    except Exception as e: 
        response = JsonResponse(data= {'Message': f'({e.__traceback__.tb_lineno}): {str(e)}'}, status= status.HTTP_503_SERVICE_UNAVAILABLE)
        logger.error(response.content.decode('utf-8'))
        await saveTaskResult(response, loads(request.body), caller )
        return response
    
@csrf_exempt
async def deleteEntry(request:ASGIRequest):
    '''
    Function Description: 
       Deletes entry records from the database on user request. 

       If any error occurs then save the status code and optional message in the database table 'BackGroundTaskDjango'. Transactions are not 
       atomic

    Param: 
        request(ASGIRequest): Request sent to endpoint from client 
    
    Returns: 
        response (JSONResponse): Communicates back to the client the result of the request. Usually just a string or an echo of the request 
    '''
    logger = setup_server_logger(loggerLevel)
    logger.info('Delete Entry Function called')
    secret = '0IQNBiGEAejNMlFmdQc8NWEiMe1Uzg01'
    if aunthenticateRequst(request, secret):
        inputData = loads(request.body)
        logger.debug(f'Input data: \n{dumps(inputData, indent= 4)}')
        
        if request.method == 'POST':
            
            def deleteEntry():
                try:
                    expense = Entry.objects.get(id=inputData['id'], workspaceId = inputData['workspaceId'])
                    expense.delete()
                    logger.info('Entry Deleted...')
                    return True
                except Entry.DoesNotExist:
                    logger.warning('Entry was not deleted successfully')
                    return False
            
            deleteAsync =  sync_to_async(deleteEntry)
            result = await deleteAsync()
            
            if result:
                response = JsonResponse(data = {
                        'Message': 'Expense Deleted',
                        'data': inputData
                    }, status=status.HTTP_200_OK)
                logger.debug(response)
                return response
            else: 
                response = JsonResponse(data=None, status= status.HTTP_204_NO_CONTENT, safe=False)
                logger.debug(response)
                return response
    else:
        response = JsonResponse(data={'Invalid Request': 'SECURITY ALERT'}, status=status.HTTP_423_LOCKED)
        await saveTaskResult(response, dumps(loads(request.body)), 'DeleteEntry Function')
        return response

@csrf_exempt
async def deleteExpense(request: ASGIRequest):
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
def requestFilesForExpense(request:ASGIRequest): 
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
                    logger.info(dumps({'Error Key': key, 'Error Value': value}, indent =4))
                raise ValidationError(serializer.errors)
        except ValidationError as e:
            return JsonResponse(data={'Message': 'Invalid Input data. Could not serialize image'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f'Caught Exception ({e.__traceback__.tb_lineno}) - {str(e)}')
            response = JsonResponse(data={'Invalid Request': f'Error Occured On server'}, status=status.HTTP_501_NOT_IMPLEMENTED)
            taskResult(response=response, inputData=inputData, caller='requestFilesForExpense')
            return response

            
