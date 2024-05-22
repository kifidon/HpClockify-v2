'''
Besides the Update approval and new Expense functions, no retry logic has been put into place for FK or PK constraints. A simple solution is to 
return a result to the client, offload the constraint handling to secondary server/port, and then resubmit the request to the endpoint. Include
a flag so infinite loops do not occur.
'''

from django.http import JsonResponse, HttpResponse
from django.core.handlers.asgi import ASGIRequest
from rest_framework.exceptions import ErrorDetail
from rest_framework.decorators import api_view
from django.views.decorators.csrf import csrf_exempt
from django.db import  utils  #, transaction
from .serializers import (
    EmployeeUserSerializer,
    TimesheetSerializer,
    TimeOffSerializer,
    ExpenseSerializer,
    EntrySerializer,

)
from .models import(
    TimeOffRequests,
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
from .clockify_util.hpUtil import asyncio, taskResult, dumps, loads, reverseForOutput, download_text_file
from . import settings

import httpx
from . Loggers import setup_server_logger
from json.decoder import JSONDecodeError

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
        logger.warning('Invalid Request')
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
                    await callBackgroungExpense()
                    
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
@api_view(['GET'])
def quickBackup(request: ASGIRequest):
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
    result = main() # General String for return output
    response = Response(data = result, status=status.HTTP_200_OK)
    logger.info(f'Quickbackup:  {response.data}, {response.status_code}')
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
    caller = 'EmployeeUser Function '
    secret  = 'v9otRjmoOBTbwkf6IaBJ4VUgRGC8QU6V'
    secret2 = 'TSnab31ks1Ml1oXkZHMIzp7R33SRSedz'
    secret3 = 'JtyuoJ1ds3tSeXB9vyPIHjRCmb0vmmDx'
    Flag = False
    if aunthenticateRequst(request, secret): 
        stat = 'ACTIVE' 
        Flag = True 
    elif not Flag and aunthenticateRequst(request, secret2):
        stat = 'ACTIVE'  
        Flag = True 
    elif not Flag and aunthenticateRequst(request, secret3): 
        stat = 'INACTIVE'
        Flag = True
    if Flag: 
        if request.method == 'POST': 
            inputData = loads(request.body)
            logger.debug(f'\nInput Is \n {reverseForOutput(inputData)}')
# decode secret to find status 
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
                await saveTaskResult(response, inputData, caller)
                return response
    else: 
        response = JsonResponse(data={'Invalid Request': 'SECURITY ALERT'}, status=status.HTTP_423_LOCKED)
        saveTaskResult(response, dumps(loads(request.body)), 'User  Function')
        return response  

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
def getProjects(request: ASGIRequest, format = None):
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
                await saveTaskResult(response, inputData, caller)
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
                await remove()
                return JsonResponse(data= {'Message': f'Deleted Time off request {inputData['id']}'}, status = status.HTTP_200_OK)
            except Exception as e: 
                response = JsonResponse(data= {'Message': f'({e.__traceback__.tb_lineno}): {str(e)}'})
                logger.error(response.data['Message'])
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
    logger = setup_server_logger(loggerLevel)
    logger.info('newExpense view called')
    secret = 'CiLrAry1UiEZb4OnPmX67T8un5GuYw24' #newExpense
    secret2 = 'l7Zqmv1BMxNPsTKKtWYEsjsHNpSfnUrj' #UpdateExpene
    if aunthenticateRequst(request, secret) or aunthenticateRequst(request, secret2):
        if request.method == 'POST':
            try:
                inputData = loads(request.body)
                RetryFlag = False
            except JSONDecodeError:
                logger.info('Called Internally')
                inputData = request.POST
                RetryFlag = True
            except Exception as e:
                logger.warning('Unknown Exception, attempting to handle')
                inputData = request.POST
                RetryFlag = True
            logger.debug(dumps(inputData, indent=4))
            
            def processExpense(inputData):
                try:
                    expense = Expense.objects.get(id=inputData['id'])
                    serializer = ExpenseSerializer(data= inputData, instance=expense)
                    logger.info('Updating Expense')
                except Expense.DoesNotExist:
                    logger.info('Inserting New Expense ')
                    serializer = ExpenseSerializer(data = inputData)
                try:
                    if serializer.is_valid():
                        serializer.save()
                        logger.info(reverseForOutput(inputData))
                        logger.info(f'Saved Expense with Id - {inputData['id']}')
                        return True, 'V' # V for valid 
                    else:
                        #force backgroung task 
                        logger.warning(f'Serializer could not be saved: {serializer.errors}')
                        for key, value in serializer.errors.items():
                            logger.info(dumps({'Error Key': key, 'Error Value': value}, indent =4))
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
                except Exception as e:
                    logger.error(f'Unknown Error Caught -{e} at {e.__traceback__.tb_lineno}')
                    return False, 'X'

            async def callBackgroungCategory():
                if not RetryFlag:
                    url =  'http://localhost:5000/HpClockifyApi/task/retryExpense'
                    async with httpx.AsyncClient(timeout=300) as client:
                        await client.post(url=url, data=inputData)
                else: 
                    logger.error('Max retries reached. Failing task')
                        
            processExpenseAsync = sync_to_async(processExpense)
            result = await processExpenseAsync(inputData)
            if result[0]:
                return JsonResponse(data=inputData, status=status.HTTP_201_CREATED) # validated data later
            elif result[1] == 'C':
                # Enqueue a background task to retry the operation
                asyncio.create_task(callBackgroungCategory()) 
                return JsonResponse(
                    data={
                        'Message': 'Foreign Key Constraint on Category. Calling background task and trying again. Review Logs for result '
                        }, status=status.HTTP_307_TEMPORARY_REDIRECT)
            elif result[1] == 'X':
                return JsonResponse(
                    data= {
                        'Message': 'Post Data could not be validated. Review Logs'
                        },
                        status=status.HTTP_400_BAD_REQUEST
                )
    else:
        response = JsonResponse(data={'Invalid Request': 'SECURITY ALERT'}, status=status.HTTP_423_LOCKED)
        taskResult(response, dumps(loads(request.body)), 'NewExpense Function')
        return response

@csrf_exempt
async def newEntry(request:ASGIRequest):
    logger = setup_server_logger()
    logger.info('newEntry view called')
    secret = 'e2kRQ3xauRrfFqkyBMsgRaCLFagJqmCE' #newEntry 
    secret2 = 'Ps4GN6oxDKYh9Q33F1BULtCI7rcgxqXW' #updateEntry  
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
                        logger.info(dumps({'Error Key': key, 'Error Value': value}, indent =4))
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
        taskResult(response, dumps(loads(request.body)), 'NewEntry Function')
        return response

@csrf_exempt
async def deleteEntry(request:ASGIRequest):
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
        taskResult(response, dumps(loads(request.body)), 'DeleteEntry Function')
        return response


@csrf_exempt
async def deleteExpense(request: ASGIRequest):
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
        taskResult(response, dumps(loads(request.body)), 'DeleteExpense Function')
        return response