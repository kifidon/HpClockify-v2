from django.http import HttpRequest, JsonResponse, HttpResponse
from rest_framework.decorators import api_view
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction , utils
from .serializers import (
    TimesheetSerializer,
    EntrySerializer,
    TagsForSerializer,

)
from .models import(
    Timesheet,
    Entry,
    Tagsfor
)
from asgiref.sync import sync_to_async
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response 
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
import os
import shutil
from .clockify_util import ClockifyPullV3
from .clockify_util.QuickBackupV3 import main, TimesheetEvent, monthlyBillable, weeklyPayroll, ClientEvent, UserEvent, ProjectEvent, TimeOffEvent, PolicyEvent
from .clockify_util import SqlClockPull
from .clockify_util.hpUtil import get_current_time, asyncio, logging, dumps, loads
from . import settings
import time

MAX_RETRIES = 3
DELAY = 0

def updateTags(entrySerilizer: EntrySerializer, request:HttpRequest, timeId, workspaceId):
    logging.info(f'{get_current_time()} - INFO: updateTags Function called')
    tags_data = entrySerilizer.validated_data.get('tags')
    entry_id = entrySerilizer.validated_data.get('id')
    # Get existing tags associated with the entry
    def deleteOldTags():
        try: 
            existing_tags = list(Tagsfor.objects.filter(entryid=entry_id, workspace=workspaceId))
                # Extract tag ids from the existing tags
            existing_tag_ids = []
            for tag in existing_tags: 
                existing_tag_ids.append(tag.id) 
            existing_tag_ids = set(existing_tag_ids)
                # Extract tag ids from the request payload
            request_tag_ids = set(tag['id'] for tag in tags_data)
                # Find tags to delete
            tags_to_delete = existing_tag_ids - request_tag_ids
            Tagsfor.objects.filter(id__in=tags_to_delete).delete()
            logging.info(f'{get_current_time()} - INFO: Deleting old tags...{tags_to_delete}')
        except Tagsfor.DoesNotExist: 
            # ('No existing taggs')
            pass
            # Find new tags to create

    def updateTags(tag): # as thread 
        # Create new tags
        try: 
            tag = Tagsfor.objects.get(id=tag['id'], entryid = entry_id, workspace = workspaceId)
            serializer = TagsForSerializer(data=tag, instance=tag, context={
                'workspaceId': workspaceId,
                'timeid': timeId,
                'entryid': entry_id
            })
        except Tagsfor.DoesNotExist:
            serializer = TagsForSerializer(data=tag, context={
                'workspaceId': workspaceId,
                'timeid': timeId,
                'entryid': entry_id
            })
            logging.warning(f'WARNING: Creating new tag')
        if serializer.is_valid():
            serializer.save()
            logging.info(f'{get_current_time()} - INFO: UpdateTags on timesheet({timeId}): E-{entry_id}-T-{tag['id']} 202 ACCEPTED') 
            data_lines = dumps(serializer.validated_data, indent=4).split('\n')
            reversed_data = '\n'.join(data_lines[::-1])
            logging.info(f'{get_current_time()} - INFO: {reversed_data}')
            return serializer.validated_data
        else: 
            #  (serializer.validated_data)
            logging.error(f'{get_current_time()} - ERROR: {serializer.error_messages}')
            raise ValidationError(serializer.errors)
    
    deleteOldTags()
    for i in range(1, len(tags_data)):
        updateTags(tags_data[i])
    logging.info(f'{get_current_time()} - INFO: Update TagsFor on Timesheet{timeId}: Complete ')
    return 1

async def updateEntries(request: HttpRequest, timeSerializer: TimesheetSerializer):
    if request.method == 'POST':
        retries = 0
        while retries < MAX_RETRIES:
            logging.info(f'\n{get_current_time()} - INFO: updateEntries Function called')
            key = ClockifyPullV3.getApiKey()
            timeId = timeSerializer.validated_data['id']
            workspaceId = timeSerializer.validated_data['workspaceId']
            stat = timeSerializer.validated_data['status']['state']
            if stat == 'APPROVED':
                allEntries = await ClockifyPullV3.getEntryForApproval(workspaceId, key, timeId, stat, 1)
                # (dumps(allEntries, indent = 4))
                # (dumps(entries, indent = 4))
                # (len(entries))
                def syncUpdateEntries(entries): # create thread 
                    try: 
                        try: # try and update if exists, otherwise create
                            approvalID = entries['approvalRequestId'] if entries['approvalRequestId'] is not None else timeId
                            # (f"{entries[i]['id']}, {workspaceId}, {approvalID} ")
                            entry = Entry.objects.get(id = entries['id'], workspace = workspaceId , time_sheet = approvalID)
                            serializer = EntrySerializer(data=entries, instance=entry, context = {'workspaceId': workspaceId,'approvalRequestId': timeId})
                            logging.info(f'{get_current_time()} - INFO: Updating Entry {entries['id']}')
                        except Entry.DoesNotExist:
                            serializer = EntrySerializer(data=entries, context = {'workspaceId': workspaceId,'approvalRequestId': timeId})
                            logging.warning(f'{get_current_time()} - WARNING: Creating new Entry on timesheet {timeId}')
                            # (json.dumps(entries, indent=3))
                        if serializer.is_valid():
                            serializer.save()
                            logging.info(f'{get_current_time()} - INFO: UpdateEntries on timesheet({timeId}): E-{entries['id']} 202 ACCEPTED') 
                            data_lines = dumps(serializer.validated_data, indent=4).split('\n')
                            reversed_data = '\n'.join(data_lines[::-1])
                            logging.info(f'{get_current_time()} - INFO: {reversed_data}')
                            updateTags(serializer, request, timeId, workspaceId)
                            return serializer.validated_data
                        else: 
                            logging.error(f'{get_current_time()} - ERROR: {serializer.error_messages}')
                            raise ValidationError(serializer.error_messages)
                    except Exception as e:
                        logging.error(f'{get_current_time()} - ERROR: {str(e)} at line {e.__traceback__.tb_lineno} in \n\t{e.__traceback__.tb_frame}') 
                        raise  e
                updateAsync = sync_to_async(syncUpdateEntries, thread_sensitive=True)
                tasks = []
                if len(allEntries) != 0:
                    for i in range(0,len(allEntries)): # updates all entries async 
                        tasks.append(
                            updateAsync(allEntries[i])
                        )
                    try:
                        await asyncio.gather(*tasks)
                        logging.info(f'{get_current_time()} - INFO: Entries added for timesheet {timeId}') 
                        return 1
                    except Exception as e:
                        logging.error(f'{get_current_time()} - ERROR: ({retries}/{MAX_RETRIES}) {str(e)} at line {e.__traceback__.tb_lineno} in \n\t{e.__traceback__.tb_frame}')
                        retries += 1 
                        time.sleep(DELAY)
                else: 
                    logging.warning(f'{get_current_time()} - WARNING: No entries were found on timesheet with id {timeId}. Review Clockify. 304 NOT_MODIFIED')
                    return 0
            else:
                logging.info(f'{get_current_time()} - WARNING: UpdateEntries on timesheet({timeId}): Update on Pending or Withdrawn timesheet not necessary  406 NOT_ACCEPTED    ')
                return 0
    else:
        logging.warning(f"{get_current_time()} - {status.HTTP_403_FORBIDDEN}")
        return 0

@csrf_exempt
async def updateTimesheets(request:HttpRequest):
    if request.method == 'POST':
        input = loads(request.body)
        logging.info(f'\n{get_current_time()} - INFO: {request.method}: updateTimesheet')
        try: 
            def updateApproval():
                # with transaction.atomic(): # if any error occurs then rollback 
                    try:
                        timesheet = Timesheet.objects.get(pk=input['id'])
                        serializer = TimesheetSerializer(instance= timesheet, data = input)
                    except Timesheet.DoesNotExist:
                        serializer = TimesheetSerializer(data=input)
                        logging.warning(f'WARNING: Adding new timesheet on update function. Timesheet { input["id"] }')
                    if serializer.is_valid():
                        serializer.save()
                        # task = asyncio.ensure_future(updateEntries(request, serializer))
                        # await asyncio.wait([task])
                        response = JsonResponse(data={
                                                'timesheet':serializer.validated_data
                                            }, status = status.HTTP_202_ACCEPTED)
                        logging.info(f'{get_current_time()} - INFO: UpdateTimesheet:{dumps(input["id"])}{response.status_code}')
                        return [response, serializer]
                    else: 
                        response = JsonResponse(data=serializer.error_messages, status=status.HTTP_400_BAD_REQUEST)
                        logging.error(f'{get_current_time()} - ERROR: UpdateTimesheet:{dumps(input["id"])}{response.status_code}')
                        return [response, None]

            updateAsync = sync_to_async(updateApproval, thread_sensitive=True)
            result = await updateAsync()
            if result[1]:
                asyncio.create_task(updateEntries(request, result[1]))
            else: 
                raise ValidationError('Unknown Error occured. Timesheet Serializer not created.')
            return result[0]
        except Exception as e:
            # transaction.rollback()
            response = JsonResponse(data= {'Message': f'{str(e)}', 'Traceback': e.__traceback__.tb_lineno}, status= status.HTTP_400_BAD_REQUEST)
            logging.error(f'{get_current_time()} - ERROR: {str(e)}')
            logging.error(f'{get_current_time()} - ERROR: {dumps(input["id"])}\n{response.status_code}')
            return response
    else:
        response = JsonResponse(data=None, status = status.HTTP_403_FORBIDDEN)
        return response
@api_view(['POST'])
def newTimeSheets(request: HttpRequest):
    logging.info(f'\n{get_current_time()} - INFO: {request.method}: newTimesheet')
    if request.method == 'POST':
        try:
            data = request.data
            serializer = TimesheetSerializer(data= data)
            if serializer.is_valid():
                serializer.save()
                response = JsonResponse(data={'timesheet':serializer.validated_data} ,status=status.HTTP_201_CREATED)
                logging.info(f'{get_current_time()} - INFO: NewTimesheet:{dumps(data["id"])}{response.status_code}')
                return response
            else:
                response = Response(data= serializer.error_messages, status=status.HTTP_400_BAD_REQUEST)
                logging.error(f'{get_current_time()} - {response}')
                return response
        except utils.IntegrityError as e:
            if 'PRIMARY KEY constraint' in str(e): 
                response = Response(data={'Message': f'Cannot create new Timesheet because id {request.data["id"]} already exists'}, status=status.HTTP_409_CONFLICT)
                logging.error(f"{get_current_time()} - ERROR: on timesheet {request.data['id']}")
                logging.error(f'{get_current_time()} - {response}')
                return response
            elif('FOREIGN KEY') in str(e): # maybe include calls to update and try again in the future 
                response = Response(data=str(e), status=status.HTTP_406_NOT_ACCEPTABLE)
                logging.error(f"{get_current_time()} -ERROR: on timesheet {request.data['id']}")
                logging.error(f'{get_current_time()} - {response}')
                return response
            else:
                response = Response(data=str(e), status = status.HTTP_400_BAD_REQUEST) 
                logging.error(f"{get_current_time()} - ERROR: on timesheet {request.data['id']}")
                logging.error(f'{get_current_time()} - {response}')
                return response
        except Exception as e:
            logging.error(f"{get_current_time()} - ERROR: on timesheet {request.data['id']}: {str(e)} at {e.__traceback__.tb_lineno}")
            response = Response(data=str(e), status=status.HTTP_503_SERVICE_UNAVAILABLE)
            logging.error(f'{get_current_time()} - {response}')
            return response
    else:
        response = Response(data=None, status = status.HTTP_403_FORBIDDEN)
        return response

@api_view(['GET'])
def quickBackup(request: HttpRequest):
    result = main() # General String for return output
    response = Response(data = result, status=status.HTTP_200_OK)
    logging.info(f'{get_current_time()} - {get_current_time()}INFO: Quickbackup:  {response.data}, {response.status_code}')
    return response

@api_view(['GET'])
def timesheets(request: HttpRequest):
    result = TimesheetEvent(status='APPROVED')
    response = Response(data = result, status=status.HTTP_200_OK)
    logging.info(f'{get_current_time()} - INFO: Quickbackup:  {response.data}, {response.status_code}')
    
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
    folder_path = monthlyBillable(start_date, end_date )
    return download_text_file(folder_path)

def weeklyPayrollReport(request, start_date=None, end_date= None):
    logging.info(f'\n{get_current_time()} - INFO: Weekly Payroll Report Called')
    folder_path = weeklyPayroll(start_date, end_date )
    (folder_path)
    return download_text_file(folder_path)

@api_view(['GET'])
def view_log(request):
    log_file_path = os.path.join(settings.LOGS_DIR, 'ServerLog.log')  # Update with the path to your logging file
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
        return HttpResponse('Logging file not found', status=404)

@api_view(['POST'])
def getClients(request: HttpRequest):
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
            stat = ClientEvent()
            logging.info(f'{get_current_time()} - Client Event: Add Client')
            if stat:
                return Response(data='Check logs @: https://hpclockifyapi.azurewebsites.net/', status=status.HTTP_200_OK)
            else: return Response(data='Check logs @: https://hpclockifyapi.azurewebsites.net/', status=status.HTTP_400_BAD_REQUEST)
        else:
            response = Response(data=None, status = status.HTTP_403_FORBIDDEN)
            return response

@api_view(['POST'])
def getEmployeeUsers(request: HttpRequest, format = None):
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
            logging.info(f'{get_current_time()} - User Event: Add User')
            if stat:
                return Response(data='Check logs @: https://hpclockifyapi.azurewebsites.net/', status=status.HTTP_200_OK)
            else: Response(data='Check logs @: https://hpclockifyapi.azurewebsites.net/', status=status.HTTP_400_BAD_REQUEST)
        else:
            response = Response(data=None, status = status.HTTP_403_FORBIDDEN)
            return response
        
@api_view(['GET', 'POST'])
def bankedHrs(request: HttpRequest):
    logging.info(f'{get_current_time()} - INFO: {request.method}: bankedHours ')
    try:
        SqlClockPull.main()
        return Response(data='Operation Completed', status=status.HTTP_200_OK)
    except Exception as e:
        logging.error(f'{get_current_time()} - ERROR: {str(e)}')
        return Response(data='Error: Check Logs @ https://hpclockifyapi.azurewebsites.net/', status=status.HTTP_406_NOT_ACCEPTABLE)

'''
@api_view(['GET', 'POST'])
def getWorkspaces(request: HttpRequest, format = None):
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
            try:
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
    #     Response(data = None, status = status.HTTP_403_FORBIDDEN)
   ''' 

@api_view(['POST'])
def getClients(request: HttpRequest):
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
            stat = ClientEvent()
            logging.info(f'{get_current_time()} - Client Event: Add Client')
            if stat:
                return Response(data='Check logs @: https://hpclockifyapi.azurewebsites.net/', status=status.HTTP_200_OK)
            else: return Response(data='Check logs @: https://hpclockifyapi.azurewebsites.net/', status=status.HTTP_400_BAD_REQUEST)
        else:
            response = Response(data=None, status = status.HTTP_403_FORBIDDEN)
            return response

@api_view(['POST'])
def getEmployeeUsers(request: HttpRequest, format = None):
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
            logging.info(f'{get_current_time()} - User Event: Add User')
            if stat:
                return Response(data='Check logs @: https://hpclockifyapi.azurewebsites.net/', status=status.HTTP_200_OK)
            else: Response(data='Check logs @: https://hpclockifyapi.azurewebsites.net/', status=status.HTTP_400_BAD_REQUEST)
        else:
            response = Response(data=None, status = status.HTTP_403_FORBIDDEN)
            return response
        
@api_view(['GET', 'POST',])
def getProjects(request: HttpRequest, format = None):
        logging.info(f'{get_current_time()} - INFO: POST: getProjects')
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
            logging.info(f'{get_current_time()} - Project Event ')
            if stat:
                return Response(data= 'Check logs @: https://hpclockifyapi.azurewebsites.net/', status=status.HTTP_200_OK)
            else: return Response(data='Check logs @: https://hpclockifyapi.azurewebsites.net/', status=status.HTTP_400_BAD_REQUEST)
        else:
            response = Response(data=None, status = status.HTTP_403_FORBIDDEN)
            return response
        
@api_view(['GET', 'POST', 'PUT', 'DELETE'])
def getTimeOffRequests(request: HttpRequest, format = None):
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
            logging.info(f'{get_current_time()} - Time Off  Event: Add Time Off')
            if stat:
                return Response(data='Check logs @: https://hpclockifyapi.azurewebsites.net/', status=status.HTTP_200_OK)
            else: return Response(data='Check logs @: https://hpclockifyapi.azurewebsites.net/', status=status.HTTP_400_BAD_REQUEST)
        else:
            response = Response(data=None, status = status.HTTP_403_FORBIDDEN)
            return response
        
@api_view(['GET', 'POST', 'PUT', 'DELETE'])
def getTimeOffPolicies(request: HttpRequest, format = None):
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
            logging.info(f'{get_current_time()} - Policy Event: Add Policy')
            if stat:
                return Response(data='Check logs @: https://hpclockifyapi.azurewebsites.net/', status=status.HTTP_200_OK)
            else: return Response(data='Check logs @: https://hpclockifyapi.azurewebsites.net/', status=status.HTTP_400_BAD_REQUEST)
        else:
            response = Response(data=None, status = status.HTTP_403_FORBIDDEN)
            return response          