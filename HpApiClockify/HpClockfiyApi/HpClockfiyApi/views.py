from django.http import JsonResponse, HttpResponse
from django.core.handlers.asgi import ASGIRequest
from rest_framework.exceptions import ErrorDetail
from rest_framework.decorators import api_view
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction , utils
from .serializers import (
    TimesheetSerializer,
    ExpenseSerializer,
    EntrySerializer
    # CategorySerializer

)
from .models import(
    Timesheet,
    Expense,
    Entry
)
from asgiref.sync import sync_to_async
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response 
from rest_framework.request import Request 
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
import os
import shutil
from .clockify_util.QuickBackupV3 import main, TimesheetEvent, monthlyBillable, weeklyPayroll, ClientEvent, UserEvent, ProjectEvent, TimeOffEvent, PolicyEvent
from .clockify_util import SqlClockPull
from .clockify_util.hpUtil import asyncio, taskResult, dumps, loads, reverseForOutput
from . import settings

import httpx
from . Loggers import setup_server_logger
from json.decoder import JSONDecodeError

loggerLevel = 'DEBUG'
logger = setup_server_logger(loggerLevel)
saveTaskResult = sync_to_async(taskResult, thread_sensitive=True)

@csrf_exempt
async def updateTimesheets(request:ASGIRequest):
    if request.method == 'POST':
        logger = setup_server_logger(loggerLevel)
        logger.info(f'{request.method}: updateTimesheet')
        try: 
            inputData = loads(request.body)
            def updateApproval():
                # with transaction.atomic(): # if any error occurs then rollback 
                    try:
                        timesheet = Timesheet.objects.get(pk=inputData['id'])
                        serializer = TimesheetSerializer(instance= timesheet, data = inputData)
                    except Timesheet.DoesNotExist:
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
                asyncio.create_task(createTask()) 
            else: 
                raise ValidationError('Unknown Error occured. Timesheet Serializer not created.')
            return result[0]
        except Exception as e:
            # transaction.rollback()
            response = JsonResponse(data= {'Message': f'{str(e)}', 'Traceback': e.__traceback__.tb_lineno}, status= status.HTTP_400_BAD_REQUEST)
            await saveTaskResult(response, inputData, 'UpdateTimesheet Function')
            logger.error(f'{dumps(inputData["id"])} - {response.status_code}')
            return response
    else:
        response = JsonResponse(data=None, status = status.HTTP_405_METHOD_NOT_ALLOWED)
        return response

@api_view(['POST'])
def newTimeSheets(request: ASGIRequest):
    logger = setup_server_logger(loggerLevel)
    logger.info(f'{request.method}: newTimesheet')
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

@api_view(['GET'])
def quickBackup(request: ASGIRequest):
    result = main() # General String for return output
    response = Response(data = result, status=status.HTTP_200_OK)
    logger.info(f'Quickbackup:  {response.data}, {response.status_code}')
    return response

@api_view(['GET'])
def timesheets(request: ASGIRequest):
    result = TimesheetEvent(status='APPROVED')
    response = Response(data = result, status=status.HTTP_200_OK)
    logger.info(f'Quickbackup:  {response.data}, {response.status_code}')
    
    return response

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
    return HttpResponse( content='Could not pull billing report. Are you sure the date parameters are in the correct form? (YYYY-MM-DD)\nReview Logs for more detail @ https://hpclockifyapi.azurewebsites.net/')

@api_view(['GET'])
def monthlyBillableReport(request, start_date = None, end_date= None):
    logger = setup_server_logger(loggerLevel)
    logger.info('BillableReport Called')
    folder_path = monthlyBillable(start_date, end_date )
    return download_text_file(folder_path)

@api_view(['GET'])
def weeklyPayrollReport(request, start_date=None, end_date= None):
    logger.info(f'Weekly Payroll Report Called')
    folder_path = weeklyPayroll(start_date, end_date )
    (folder_path)
    return download_text_file(folder_path)

@api_view(['GET'])
def viewServerLog(request):
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
        return HttpResponse(log_contents, content_type='text/plain')
    else:
        return HttpResponse('logger file not found', status=404)

@api_view(['GET'])
def viewTaskLog(request):
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
        return HttpResponse(log_contents, content_type='text/plain')
    else:
        return HttpResponse('logger file not found', status=404)
    

@api_view(['POST'])
def getClients(request: ASGIRequest):
    # for security 
    # signature = request.headers.get('X-Clockify-Signature') # or wherever the signing secret is held 
    # payload = request.body
    # secret = b'' # input signing secret here 
    # auth = hmac.compare_digest(secret,payload,hashlib.sha256).hexdigest()
    # if hmac.compare_digest(auth, signature):   
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

@api_view(['POST'])
def getEmployeeUsers(request: ASGIRequest, format = None):
    # signature = request.headers.get('X-Clockify-Signature') # or wherever the signing secret is held 
    # payload = request.body
    # secret = b'' # input signing secret here 
    # auth = hmac.compare_digest(secret,payload,hashlib.sha256).hexdigest()
    # if hmac.compare_digest(auth, signature):   
        '''
        if request.method == 'GET':
            user = Employeeuser.objects.all()
            serializer = EmployeeUserSerializer(user, many=True)
            response = Response(serializer.data )
        '''
        if request.method == 'POST' or request.method=='GET':
            stat = UserEvent()
            logger.info(f'User Event: Add User')
            if stat:
                return Response(data='Check logs @: https://hpclockifyapi.azurewebsites.net/', status=status.HTTP_200_OK)
            else: Response(data='Check logs @: https://hpclockifyapi.azurewebsites.net/', status=status.HTTP_400_BAD_REQUEST)
        else:
            response = Response(data=None, status = status.HTTP_405_METHOD_NOT_ALLOWED)
            return response
        
@api_view(['GET', 'POST'])
def bankedHrs(request: ASGIRequest):
    logger.info(f'{request.method}: bankedHours ')
    try:
        SqlClockPull.main()
        return Response(data='Operation Completed', status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f'{str(e)}')
        return Response(data='Error: Check Logs @ https://hpclockifyapi.azurewebsites.net/', status=status.HTTP_406_NOT_ACCEPTABLE)

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

@api_view(['POST'])
def getClients(request: ASGIRequest):
    # for security 
    # signature = request.headers.get('X-Clockify-Signature') # or wherever the signing secret is held 
    # payload = request.body
    # secret = b'' # input signing secret here 
    # auth = hmac.compare_digest(secret,payload,hashlib.sha256).hexdigest()
    # if hmac.compare_digest(auth, signature):   
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

@api_view(['POST'])
def getEmployeeUsers(request: ASGIRequest, format = None):
    # signature = request.headers.get('X-Clockify-Signature') # or wherever the signing secret is held 
    # payload = request.body
    # secret = b'' # input signing secret here 
    # auth = hmac.compare_digest(secret,payload,hashlib.sha256).hexdigest()
    # if hmac.compare_digest(auth, signature):   
        '''
        if request.method == 'GET':
            user = Employeeuser.objects.all()
            serializer = EmployeeUserSerializer(user, many=True)
            response = Response(serializer.data )
        '''
        if request.method == 'POST' or request.method=='GET':
            stat = UserEvent()
            logger.info(f'User Event: Add User')
            if stat:
                return Response(data='Check logs @: https://hpclockifyapi.azurewebsites.net/', status=status.HTTP_200_OK)
            else: Response(data='Check logs @: https://hpclockifyapi.azurewebsites.net/', status=status.HTTP_400_BAD_REQUEST)
        else:
            response = Response(data=None, status = status.HTTP_405_METHOD_NOT_ALLOWED)
            return response
        
@api_view(['GET', 'POST',])
def getProjects(request: ASGIRequest, format = None):
        logger.info(f'POST: getProjects')
    # signature = request.headers.get('X-Clockify-Signature') # or wherever the signing secret is held 
    # payload = request.body
    # secret = b'' # input signing secret here 
    # auth = hmac.compare_digest(secret,payload,hashlib.sha256).hexdigest()
    # if hmac.compare_digest(auth, signature):   
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
        
@api_view(['GET', 'POST', 'PUT', 'DELETE'])
def getTimeOffRequests(request: ASGIRequest, format = None):
    # signature = request.headers.get('X-Clockify-Signature') # or wherever the signing secret is held 
    # payload = request.body
    # secret = b'' # input signing secret here 
    # auth = hmac.compare_digest(secret,payload,hashlib.sha256).hexdigest()
    # if hmac.compare_digest(auth, signature):   
        '''
        
        elif request.method == 'GET':
            timeOff = Timeoffrequests.objects.all()
            serializer = TimeOffRequestsSerializer(timeOff, many=True)
            response = Response(serializer.data, status= status.HTTP_200_OK)
        '''
        if request.method == 'POST' or request.method == 'GET':
            stat = TimeOffEvent()
            logger.info(f'Time Off  Event: Add Time Off')
            if stat:
                return Response(data='Check logs @: https://hpclockifyapi.azurewebsites.net/', status=status.HTTP_200_OK)
            else: return Response(data='Check logs @: https://hpclockifyapi.azurewebsites.net/', status=status.HTTP_400_BAD_REQUEST)
        else:
            response = Response(data=None, status = status.HTTP_405_METHOD_NOT_ALLOWED)
            return response
        w
@api_view(['GET', 'POST', 'PUT', 'DELETE'])
def getTimeOffPolicies(request: ASGIRequest, format = None):
    # signature = request.headers.get('X-Clockify-Signature') # or wherever the signing secret is held 
    # payload = request.body
    # secret = b'' # input signing secret here 
    # auth = hmac.compare_digest(secret,payload,hashlib.sha256).hexdigest()
    # if hmac.compare_digest(auth, signature):   
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
                    logger.info(dumps(inputData, indent= 4))
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

@csrf_exempt
async def newEntry(request:ASGIRequest):
    logger = setup_server_logger()
    logger.info('newEntry view called')
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

@csrf_exempt
async def deleteEntry(request:ASGIRequest):
    logger = setup_server_logger(loggerLevel)
    logger.info('Delete Entry Function called')
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

    
@csrf_exempt
async def deleteExpense(request: ASGIRequest):
    logger = setup_server_logger(loggerLevel)
    logger.info('Delete Expense Function called')
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
    
