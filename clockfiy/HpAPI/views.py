from django.http import HttpRequest
from django.db import transaction
import json
from .models import (
    Timesheet,
    Project,
    Entry,
    Tagsfor,
)
from django.db import utils
from .serializers import (

    TimeSheetSerializer,
    EntrySerializer,
    TagsForSerializer
)
# from adrf.decorators import api_view
from asgiref.sync import sync_to_async
from rest_framework.decorators import api_view
# from adrf.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from . import ClockifyPullV2
from django.http import HttpResponse
import os
from . import settings
from . import QuickBackupV2
import logging
from rest_framework.exceptions import ValidationError
import shutil
from django.views.decorators.csrf import csrf_exempt
from . import  SqlClockPull
from datetime import datetime
import asyncio
def get_current_time():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# @api_view(['GET'])
# def quickBackup(request: HttpRequest):
#     result = QuickBackupV2.main() # General String for return output
#     response = Response(data = result, status=status.HTTP_200_OK)
#     logging.info(f'{get_current_time()} - {get_current_time()}INFO: Quickbackup:  {response.data}, {response.status_code}')
#     return response

# @api_view(['GET'])
# def timesheets(request: HttpRequest):
#     result = QuickBackupV2.TimesheetEvent(status='APPROVED')
#     response = Response(data = result, status=status.HTTP_200_OK)
#     logging.info(f'{get_current_time()} - INFO: Quickbackup:  {response.data}, {response.status_code}')
    
#     return response

# @csrf_exempt
# def download_text_file(request, start_date = None, end_date= None):
#     folder_path = QuickBackupV2.monthlyBillable(start_date, end_date )
#     if folder_path:
#         temp_dir = f'{folder_path}_tmp'
#         os.makedirs(temp_dir, exist_ok=True)
#         # Compress the folder into a zip file
#         shutil.make_archive(temp_dir, 'zip', folder_path)
#         # Get the zip file path
#         zip_file_path = f'{temp_dir}.zip'

#         with open(zip_file_path, 'rb') as file:
#             response = HttpResponse(file.read(), content_type='application/zip')
#             response['Content-Disposition'] = f'attachment; filename="{os.path.basename(zip_file_path)}"'
#         shutil.rmtree(temp_dir)
#         os.remove(zip_file_path)
#         return response
#     return HttpResponse( content='Could not pull billing report. Are you sure the date parameters are in the correct form? (YYYY-MM-DD)\nReview Logs for more detail @ https://hpclockifyapi.azurewebsites.net/')

# '''
# @api_view(['GET', 'POST'])
# def getWorkspaces(request: HttpRequest, format = None):
#     # signature = request.headers.get('X-Clockify-Signature') # or wherever the signing secret is held 
#     # payload = request.body
#     # secret = b'' # input signing secret here 
#     # auth = hmac.compare_digest(secret,payload,hashlib.sha256).hexdigest()
#     # if hmac.compare_digest(auth, signature):
#         if request.method == 'GET':
#             workspaces = Workspace.objects.all()
#             serializer = WorkspaceSerializer(workspaces, many=True)
#             response = Response(serializer.data)
#         elif request.method == 'POST':
#             try:
#                 serializer = WorkspaceSerializer(data = request.data)
#                 if serializer.is_valid():
#                     serializer.save()
#                     return(Response(serializer.data, status = status.HTTP_201_CREATED))
#                 return ( Response( serializer.data, status = status.HTTP_400_BAD_REQUEST))
#             except Exception as e:
#                 return (Response(data = None, status=status.HTTP_417_EXPECTATION_FAILED))
#         else:
#             response = Response(data=None, status=status.HTTP_405_METHOD_NOT_ALLOWED)
#     # else: 
#     #     Response(data = None, status = status.HTTP_403_FORBIDDEN)
    
# '''
# @api_view(['POST'])
# def getClients(request: HttpRequest):
#     # signature = request.headers.get('X-Clockify-Signature') # or wherever the signing secret is held 
#     # payload = request.body
#     # secret = b'' # input signing secret here 
#     # auth = hmac.compare_digest(secret,payload,hashlib.sha256).hexdigest()
#     # if hmac.compare_digest(auth, signature):   
#         '''    
#         if request.method == 'GET':
#             clients = Client.objects.all()
#             serializer = ClientSerializer(clients, many=True)
#             response = Response(serializer.data )
#         elif request.method == 'PUT':
#             try: 
#                 client = Client.objects.get(pk=request['id'])
#                 serializer = ClientSerializer(instance= client, data = request.data)
#                 if serializer.is_valid():
#                     serializer.save()
#                     response = Response( data= serializer.data, status= status.HTTP_202_ACCEPTED)
#                 return(Response(serializer.data, status= status.HTTP_400_BAD_REQUEST))
#             except Client.DoesNotExist:
#                 response = Response(data= serializer.data, status= status.HTTP_203_NON_AUTHORITATIVE_INFORMATION)
#             except utils.IntegrityError as e:
#                 if 'PRIMARY KEY constraint' in str(e): 
#                     response = Response(serializer.data, status=status.HTTP_304_NOT_MODIFIED)
#                 elif('FOREIGN KEY') in str(e): # maybe include calls to update and try again in the future 
#                     response = Response(serializer.data, status=status.HTTP_406_NOT_ACCEPTABLE)
#                 else:
#                     response = Response(serializer.data, status = status.HTTP_400_BAD_REQUEST) 
#         '''    
#         if request.method == 'POST':
#             stat = QuickBackupV2.ClientEvent()
#             logging.info(f'{get_current_time()} - Client Event: Add Client')
#             if stat:
#                 return Response(data='Check logs @: https://hpclockifyapi.azurewebsites.net/', status=status.HTTP_200_OK)
#             else: return Response(data='Check logs @: https://hpclockifyapi.azurewebsites.net/', status=status.HTTP_400_BAD_REQUEST)
#         else:
#             response = Response(data=None, status = status.HTTP_403_FORBIDDEN)
#             return response
#         '''
#         elif request.method == 'DELETE':
#             try:
#                 client = Client.objects.get(pk=request['id'])
#                 client.delete()
#                 response = Response(data = None, status=status.HTTP_200_OK)
#             except Client.DoesNotExist:
#                 response = Response(data=None, status= status.HTTP_204_NO_CONTENT)
#         else:
#             response = Response(data=None, status=status.HTTP_405_METHOD_NOT_ALLOWED)
#     # else:
#     #     response = Response(data=None, status = status.HTTP_403_FORBIDDEN)
#         '''

# @api_view(['POST'])
# def getEmployeeUsers(request: HttpRequest, format = None):
#     # signature = request.headers.get('X-Clockify-Signature') # or wherever the signing secret is held 
#     # payload = request.body
#     # secret = b'' # input signing secret here 
#     # auth = hmac.compare_digest(secret,payload,hashlib.sha256).hexdigest()
#     # if hmac.compare_digest(auth, signature):   
#         '''
#         if request.method == 'GET':
#             user = Employeeuser.objects.all()
#             serializer = EmployeeUserSerializer(user, many=True)
#             response = Response(serializer.data )
#         elif request.method == 'PUT':
#             try: 
#                 user = Employeeuser.objects.get(pk=request['id'])
#                 serializer = EmployeeUserSerializer(instance= user, data = request.data)
#                 if serializer.is_valid():
#                     serializer.save()
#                     response = Response( data= serializer.data, status= status.HTTP_202_ACCEPTED)
#                 return(Response(serializer.data, status= status.HTTP_400_BAD_REQUEST))
#             except Employeeuser.DoesNotExist:
#                 response = Response(data= serializer.data, status= status.HTTP_203_NON_AUTHORITATIVE_INFORMATION)
#             except utils.IntegrityError as e:
#                 if 'PRIMARY KEY constraint' in str(e): 
#                     response = Response(serializer.data, status=status.HTTP_304_NOT_MODIFIED)
#                 elif('FOREIGN KEY') in str(e): # maybe include calls to update and try again in the future 
#                     response = Response(serializer.data, status=status.HTTP_406_NOT_ACCEPTABLE)
#                 else:
#                     response = Response(serializer.data, status = status.HTTP_400_BAD_REQUEST) 
#         '''
#         if request.method == 'POST' or request.method=='GET':
#             stat = QuickBackupV2.UserEvent()
#             logging.info(f'{get_current_time()} - User Event: Add User')
#             if stat:
#                 return Response(data='Check logs @: https://hpclockifyapi.azurewebsites.net/', status=status.HTTP_200_OK)
#             else: Response(data='Check logs @: https://hpclockifyapi.azurewebsites.net/', status=status.HTTP_400_BAD_REQUEST)
#         else:
#             response = Response(data=None, status = status.HTTP_403_FORBIDDEN)
#             return response
#         '''
#         elif request.method == 'DELETE':
#             try:
#                 user = Employeeuser.objects.get(pk=request['id'])
#                 user.delete()
#                 response = Response(data = None, status=status.HTTP_200_OK)
#             except Employeeuser.DoesNotExist:
#                 response = Response(data=None, status= status.HTTP_204_NO_CONTENT)
#         else:
#             response = Response(data=None, status=status.HTTP_405_METHOD_NOT_ALLOWED)
#     # else:
#     #     response = Response(data=None, status = status.HTTP_403_FORBIDDEN)
#         '''

# @api_view(['GET', 'POST'])
# def bankedHrs(request: HttpRequest):
#     logging.info(f'{get_current_time()} - INFO: {request.method}: bankedHours ')
#     try:
#         SqlClockPull.main()
#         return Response(data='Operation Completed', status=status.HTTP_200_OK)
#     except Exception as e:
#         logging.error(f'{get_current_time()} - ERROR: {str(e)}')
#         return Response(data='Error: Check Logs @ https://hpclockifyapi.azurewebsites.net/', status=status.HTTP_406_NOT_ACCEPTABLE)

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

@sync_to_async
def updateTags(entrySerilizer: EntrySerializer, request, timeId, workspaceId):
    logging.info(f'{get_current_time()} - INFO: updateTags Function called')
    tags_data = entrySerilizer.validated_data.get('tags')
    entry_id = entrySerilizer.validated_data.get('id')
        # Get existing tags associated with the entry
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
        # print('No existing taggs')
        pass
        # Find new tags to create
    i = 0 
    serializers = []
    while i < len(tags_data):
        # Create new tags
        try: 
            tag = Tagsfor.objects.get(id=tags_data[i]['id'], entryid = entry_id, workspace = workspaceId)
            serializer = TagsForSerializer(data=tags_data[i], instance=tag, context={
                'workspaceId': workspaceId,
                'timeid': timeId,
                'entryid': entry_id
            })
        except Tagsfor.DoesNotExist:
            serializer = TagsForSerializer(data=tags_data[i], context={
                'workspaceId': workspaceId,
                'timeid': timeId,
                'entryid': entry_id
            })
            logging.warning(f'WARNING: Creating new tag')
        i += 1
        if serializer.is_valid():
            serializer.save()
            serializers.append(serializer.validated_data)
        else: 
            # print (serializer.validated_data)
            raise ValidationError(serializer.errors)
    response = Response(data= serializers, status = status.HTTP_202_ACCEPTED)
    logging.info(f'{get_current_time()} - INFO: Update Tags: {response}')
    return response

@sync_to_async
def updateEntries(request, timeSerializer):
    logging.info(f'{get_current_time()} - INFO: updateEntries Function called')
    key = ClockifyPullV2.getApiKey()
    timeId = timeSerializer.validated_data['id']
    # print (timeId)
    workspaceId = timeSerializer.validated_data['workspaceId']
    stat = timeSerializer.validated_data['status']['state']
    if stat == 'APPROVED':
        entries = ClockifyPullV2.getEntryForApproval(workspaceId, key, timeId, stat, 1)
        # print(json.dumps(entries, indent = 4))
        i = 0
        serializers = []
        while i < len(entries):
            try: 
                approvalID = entries[i]['approvalRequestId'] if entries[i]['approvalRequestId'] is not None else timeId
                entry = Entry.objects.get(id = entries[i]['id'], workspace = workspaceId , time_sheet = approvalID)
                serializer = EntrySerializer(data=entries[i], instance=entry, context = {'workspaceId': workspaceId,'approvalRequestId': timeId})
                i += 1
            except Entry.DoesNotExist:
                serializer = EntrySerializer(data=entries[i], context = {'workspaceId': workspaceId,'approvalRequestId': timeId})
                logging.warning(f'WARNING: Creating new Entry on timesheet {timeId}')
                i += 1
                # print(json.dumps(entries, indent=3))
            if serializer.is_valid():
                serializer.save()
                tagResponse = updateTags(serializer, request, timeId, workspaceId)
                serializers.append(serializer.validated_data)
            else: 
                logging.error(f'{get_current_time()} - {serializer.error_messages}')
                raise ValidationError(serializer.error_messages)
        response = Response(data = {'entry': serializers}, status = status.HTTP_202_ACCEPTED)
        logging.info(f'{get_current_time()} - INFO: UpdateEntries: {response}')
        return response
    else:
        response = Response(data={'entry': 'No Entries'}, status=status.HTTP_200_OK)
        logging.info(f'{get_current_time()} - INFO: updateEntries{response}')
        return response

#@api_view(['POST'])
@api_view(['POST'])
async def updateTimesheet(request:HttpRequest):
    if request.method == 'POST':
        logging.info(f'{get_current_time()} - \nINFO: {request.method}: updateTimesheet')
        try: 
            with transaction.atomic():
                try:
                    timesheet = Timesheet.objects.get(pk=request.data['id'])
                    serializer = TimeSheetSerializer(instance= timesheet, data = request.data)
                except Timesheet.DoesNotExist:
                    serializer = TimeSheetSerializer(data=request.data)
                    logging.warning(f'WARNING: Adding new timesheet on update function. Timesheet { request.data["id"] }')
                if serializer.is_valid():
                    serializer.save()
                    # task = asyncio.ensure_future(updateEntries(request, serializer))
                    # await asyncio.wait([task])
                    response = Response(data ={
                                            'timesheet':serializer.validated_data
                                        }, status = status.HTTP_202_ACCEPTED)
                    logging.info(f'{get_current_time()} - INFO: UpdateTimesheet:{json.dumps(request.data["id"])}{response.status_code}')
                    return response
                else: 
                    response = Response(data=serializer.error_messages, status=status.HTTP_400_BAD_REQUEST)
                    logging.error(f'{get_current_time()} - ERROR: UpdateTimesheet:{json.dumps(request.data["id"])}{response.status_code}')
                    return response
        except Exception as e:
            transaction.rollback()
            response = Response(data= {'Message': str(e)}, status= status.HTTP_400_BAD_REQUEST)
            logging.error(f'{get_current_time()} - ERROR: {str(e)}')
            logging.error(f'{get_current_time()} - ERROR:{json.dumps(request.data["id"])}\n{response.status_code}')
            return response
    else:
        response = Response(data=None, status = status.HTTP_403_FORBIDDEN)
        return response
    
# # depreciated
# def loadTags(entrySerilizer: EntrySerializer, request: HttpRequest = None, timeId: str = None, workspaceId: str = None):
#     serializers = []
#     if request.method == 'POST': # called from Entry< Put >
#         try:
#             # print (entrySerilizer)
#             tags_data = entrySerilizer.validated_data.get('tags')
#             entry_id = entrySerilizer.validated_data.get('id')
#                 # Get existing tags associated with the entry
#             try: 
#                 existing_tags = list(Tagsfor.objects.filter(entryid=entry_id, workspace=workspaceId))
#                     # Extract tag ids from the existing tags
#                 existing_tag_ids = []
#                 for tag in existing_tags: 
#                     existing_tag_ids.append(tag.id) 
#                 existing_tag_ids = set(existing_tag_ids)
#                     # Extract tag ids from the request payload
#                 request_tag_ids = set(tag['id'] for tag in tags_data)
#                     # Find tags to delete
#                 tags_to_delete = existing_tag_ids - request_tag_ids
#                 Tagsfor.objects.filter(id__in=tags_to_delete).delete()
#             except Tagsfor.DoesNotExist: 
#                 # print('No existing taggs')
#                 pass
#                 # Find new tags to create
#             i = 0
#             while i < len(tags_data):
#                 # Create new tags
#                 try: 
#                     tag = Tagsfor.objects.get(id=tags_data[i]['id'], entryid = entry_id, workspace = workspaceId)
#                     serializer = TagsForSerializer(data=tags_data[i], instance=tag, context={
#                         'workspaceId': workspaceId,
#                         'timeid': timeId,
#                         'entryid': entry_id
#                     })
#                 except Tagsfor.DoesNotExist:
#                     serializer = TagsForSerializer(data=tags_data[i], context={
#                         'workspaceId': workspaceId,
#                         'timeid': timeId,
#                         'entryid': entry_id
#                     })
#                 i += 1
#                 if serializer.is_valid():
#                     serializer.save()
#                     serializers.append(serializer.validated_data)
#                 else: 
#                     print (serializer.validated_data)
#                     response = Response(data = [serializer.errors], status = status.HTTP_400_BAD_REQUEST)
#             response = Response(data= serializers, status = status.HTTP_202_ACCEPTED)
#             logging.info(response)
#             return response
#         except Exception as e:
#             print(e)
#             response = Response(data=[str(e)], status= status.HTTP_400_BAD_REQUEST) 
#             logging.error(f'{get_current_time()} - {response}')
#             return response

# #depreciated 
# def loadEntries( request: HttpRequest, timeSerilizer: TimeSheetSerializer = None, ):
#     key = ClockifyPullV2.getApiKey()
#     timeId = timeSerilizer.validated_data['id']
#     # print (timeId)
#     workspaceId = timeSerilizer.validated_data['workspaceId']
#     stat = timeSerilizer.validated_data['status']['state']
#     entries = ClockifyPullV2.getEntryForApproval(workspaceId, key, timeId, stat, 1)
#     if len(entries) >0:
#         print (json.dumps(entries, indent=4))
#         if request.method == 'POST':
#             serializer = EntrySerializer(data = entries,  context = {'workspaceId': workspaceId,'approvalRequestId': timeId}, many= True)
#             if serializer.is_valid():
#                 serializer.save()
#                 tagResponse = loadTags(serializer, request, timeId, workspaceId)
#                 response = Response(data = {'entryS':serializer.validated_data, 'tagResponse': tagResponse }, status=status.HTTP_201_CREATED)
#                 logging.info(response)
#                 return response
#             else: 
#                 response = Response(data= {'entryS': serializer.errors}, status = status.HTTP_400_BAD_REQUEST)
#                 logging.error(f'{get_current_time()} - {response}')
#                 return response
#         else:
#             response = Response(data= 'Invalid method', status = status.HTTP_400_BAD_REQUEST)
#             logging.error(f'{get_current_time()} - {response}')
#             return response 
#     else: 
#         response = Response(data= {'entryS':'No Entries or timesheet is pending'}, status=status.HTTP_202_ACCEPTED) 
#         logging.info(response)
#         return response

# @api_view([ 'POST'])
# def getTimeSheets(request: HttpRequest, format = None):
#         logging.debug(f'{get_current_time()} - \n{request.method}')
#         logging.info(f'{get_current_time()} - INFO: getTimesheet... {request.data["id"]}')
#         '''
#         # signature = request.headers.get('X-Clockify-Signature') # or wherever the signing secret is held 
#         # payload = request.body
#         # secret = b'' # input signing secret here 
#         # auth = hmac.compare_digest(secret,payload,hashlib.sha256).hexdigest()
#         # if hmac.compare_digest(auth, signature):   
#             if request.method == 'GET':
#                 timesheet = Timesheet.objects.all()
#                 serializer = TimeSheetSerializer(timesheet, many=True)
#                 response = Response(serializer.data )
#             elif request.method == 'PUT':
#                 try: 
#                     timesheet = Timesheet.objects.get(pk=request.data['id'])
#                     serializer = TimeSheetSerializer(instance= timesheet, data = request.data)
#                     if serializer.is_valid():
#                         serializer.save() 
#                         entryReponse = loadEntries(request, serializer)
#                         entryData = entryReponse.data
#                         # print(entryData)
#                         if entryReponse.status_code >= 200 and entryReponse.status_code <= 299: # entries were saved properly
#                             tagResponse = entryData.get('tagResponse')
#                             if tagResponse is not None and  tagResponse.status_code >=200 and tagResponse.status_code <=299:
#                                 return( Response( 
#                                     data ={
#                                         'timesheet':serializer.validated_data, 
#                                         'entry': entryData.get('entryS'),
#                                         'tag': tagResponse.data
#                                     }, status = status.HTTP_202_ACCEPTED))
#                             else: response = Response(data= entryData, status =status.HTTP_207_MULTI_STATUS)
#                         else: Response(data= entryData, status= status.HTTP_207_MULTI_STATUS)
#                     return(Response(serializer.errors, status= status.HTTP_400_BAD_REQUEST))
#                 except Timesheet.DoesNotExist:
#                     response = Response('Timesheet Does Not Exists', status= status.HTTP_203_NON_AUTHORITATIVE_INFORMATION)
#                 except utils.IntegrityError as e:
#                     if 'PRIMARY KEY constraint' in str(e): 
#                         # print(str(e))
#                         response = Response(data ={
#                                         'timesheet':serializer.validated_data, 
#                                         'entry': entryData.get('entryS').validated_data,
                    
#                                         'tag': tagResponse.data.validated_data 
#                                     }, status=status.HTTP_304_NOT_MODIFIED)
#                     elif('FOREIGN KEY') in str(e): # maybe include calls to update and try again in the future 
#                         response = Response(serializer.data, status=status.HTTP_406_NOT_ACCEPTABLE)
#                     else:
#                         response = Response(serializer.data, status = status.HTTP_400_BAD_REQUEST)    
#         '''
#         if request.method == 'POST':
#             try:
#                 data = request.data
#                 serializer = TimeSheetSerializer(data= data)
#                 if serializer.is_valid():
#                     serializer.save()
#                     # store entries and then return 
#                     '''
#                     entryReponse = loadEntries(request, serializer)
#                     entryData = entryReponse.data
#                     if entryReponse.status_code >= 200 and entryReponse.status_code <= 299: # entries were saved properly
#                         tagResponse = entryData.get('tagResponse')
#                         if tagResponse is not None and tagResponse.status_code >=200 and tagResponse.status_code <=299:
#                             response = Response( 
#                                 data ={
#                                     'timesheet':serializer.validated_data, 
#                                     'entry': entryData.get('entryS'),
#                                     'tag': tagResponse.data 
#                                 }, status = status.HTTP_201_CREATED)
#                             logging.info(response)
#                             return response
#                         else: 
#                             response = Response(data= entryData, status =status.HTTP_201_CREATED)
#                             logging.info(response)
#                             return response
#                     else: 
#                         response = Response(data= {'entry_data': entryReponse.data}, status= status.HTTP_201_CREATED)
#                     '''
#                     response = Response( data= serializer.validated_data, status = status.HTTP_201_CREATED)
#                     logging.info(response)
#                     return response
#                 else:
#                     response = Response(data= serializer.error_messages, status=status.HTTP_400_BAD_REQUEST)
#                     logging.error(f'{get_current_time()} - {response}')
#                     return response
#             except utils.IntegrityError as e:
#                 if 'PRIMARY KEY constraint' in str(e): 
#                     response = Response(data={'Constraint':  str(e)}, status=status.HTTP_304_NOT_MODIFIED)
#                     logging.error(f"{get_current_time()} - ERROR: on timesheet {request.data['id']}")
#                     logging.error(f'{get_current_time()} - {response}')
#                     return response
#                 elif('FOREIGN KEY') in str(e): # maybe include calls to update and try again in the future 
#                     response = Response(data=str(e), status=status.HTTP_406_NOT_ACCEPTABLE)
#                     logging.error(f"{get_current_time()} -ERROR: on timesheet {request.data['id']}")
#                     logging.error(f'{get_current_time()} - {response}')
#                     return response
#                 else:
#                     response = Response(data=str(e), status = status.HTTP_400_BAD_REQUEST) 
#                     logging.error(f"{get_current_time()} - ERROR: on timesheet {request.data['id']}")
#                     logging.error(f'{get_current_time()} - {response}')
#                     return response
#             except Exception as e:
#                 logging.error(f"{get_current_time()} - ERROR: on timesheet {request.data['id']}")
#                 response = Response(data=str(e), status=status.HTTP_503_SERVICE_UNAVAILABLE)
#                 logging.error(f'{get_current_time()} - {response}')
#         else:
#             response = Response(data=None, status = status.HTTP_403_FORBIDDEN)
#             return response
# '''
#         elif request.method == 'DELETE':
#         try:
#             timesheet = Timesheet.objects.get(pk=request['id'])
#             timesheet.delete()
#             response = Response(data = None, status=status.HTTP_200_OK)
#         except Timesheet.DoesNotExist:
#             response = Response(data=None, status= status.HTTP_204_NO_CONTENT)
#     else:
#         response = Response(data=None, status=status.HTTP_405_METHOD_NOT_ALLOWED)
# # else:
# #     response = Response(data=None, status = status.HTTP_403_FORBIDDEN)
# '''

# @api_view(['GET', 'POST',])
# def getProjects(request: HttpRequest, format = None):
#         logging.info(f'{get_current_time()} - INFO: POST: getProjects')
#     # signature = request.headers.get('X-Clockify-Signature') # or wherever the signing secret is held 
#     # payload = request.body
#     # secret = b'' # input signing secret here 
#     # auth = hmac.compare_digest(secret,payload,hashlib.sha256).hexdigest()
#     # if hmac.compare_digest(auth, signature):   
#         if request.method == 'POST':
#             try:
#                 try:
#                     project = Project.objects.get(pk=request.data['id'])
#                     serializer = ProjectSerializer(data=request.data, instance= project)
#                 except Project.DoesNotExist:
#                     serializer = ProjectSerializer(data = request.data)
#                 if serializer.is_valid():
#                     # # print(serializer.data)
#                     serializer.save()
#                     response = Response(serializer.data, status = status.HTTP_201_CREATED)
#                     logging.info(f'{get_current_time()} - INFO: {response.data["id"]}, {response.status_code}')
#                     return response
#                 response = Response(serializer.error_messages, status = status.HTTP_400_BAD_REQUEST)
#                 logging.info(f'{get_current_time()} - ERROR: {response.data}, {response.status_code}')
#                 return response
#             except utils.IntegrityError as e:
#                 if 'PRIMARY KEY constraint' in str(e):
#                     response = Response(serializer.data, status=status.HTTP_304_NOT_MODIFIED)
#                     logging.info(f'{get_current_time()} - ERROR: {response.data}, {response.status_code}')
#                     return response
#                 elif('FOREIGN KEY') in str(e):
#                     response = Response(serializer.data, status=status.HTTP_406_NOT_ACCEPTABLE)
#                     logging.info(f'{get_current_time()} - ERROR: {response.data}, {response.status_code}')
#                     return response
#                 else:
#                     response = Response(serializer.data, status = status.HTTP_400_BAD_REQUEST)
#                     logging.info(f'{get_current_time()} - ERROR: {response.data}, {response.status_code}')
#                     return response
#         if request.method == 'GET': 
#             stat = QuickBackupV2.ProjectEvent()
#             logging.info(f'{get_current_time()} - Project Event ')
#             if stat:
#                 return Response(data= 'Check logs @: https://hpclockifyapi.azurewebsites.net/', status=status.HTTP_200_OK)
#             else: return Response(data='Check logs @: https://hpclockifyapi.azurewebsites.net/', status=status.HTTP_400_BAD_REQUEST)
#         else:
#             response = Response(data=None, status = status.HTTP_403_FORBIDDEN)
#             return response
#         '''
#         elif request.method == 'PUT':
#             try:
#                 project = Project.objects.get(pk=request.data['id'])
#                 serializer = ProjectSerializer(instance=project, data=request.data)
#                 if serializer.is_valid():
#                     serializer.save()
#                     return(Response(serializer.data, status=status.HTTP_202_ACCEPTED))
#                 else: 
#                     return(Response(serializer.data, status= status.HTTP_400_BAD_REQUEST))
#             except Project.DoesNotExist:
#                 response = Response(serializer.data, status=status.HTTP_203_NON_AUTHORITATIVE_INFORMATION)
#             except utils.IntegrityError as e:
#                 if('FOREIGN KEY') in str(e):
#                     response = Response(serializer.data, status=status.HTTP_406_NOT_ACCEPTABLE)
#                 else:
#                     response = Response(serializer.data, status = status.HTTP_400_BAD_REQUEST)
#         elif request.method == 'GET':
#             projects = Project.objects.all()
#             serializer = ProjectSerializer(projects, many=True)
#             response = Response(serializer.data, status= status.HTTP_200_OK)
#         elif request.method == 'DELETE':
#             try:
#                 project = Project.objects.get(pk=request['id'])
#                 project.delete()
#                 response = Response(data = None, status=status.HTTP_200_OK)
#             except Project.DoesNotExist:
#                 response = Response(data=None, status= status.HTTP_204_NO_CONTENT)
#         else:
#             response = Response(data=None, status=status.HTTP_405_METHOD_NOT_ALLOWED)
#         '''

# '''   
# @api_view(['GET', 'POST', 'PUT', 'DELETE'])
# def getEntries(request: HttpRequest, format = None):
#     # signature = request.headers.get('X-Clockify-Signature') # or wherever the signing secret is held 
#     # payload = request.body
#     # secret = b'' # input signing secret here 
#     # auth = hmac.compare_digest(secret,payload,hashlib.sha256).hexdigest()
#     # if hmac.compare_digest(auth, signature):   
#         if request.method == 'POST':
#             try:
#                 serializer = EntrySerializer(data = request.data)
#                 if serializer.is_valid():
#                     # # print(serializer.data)
#                     serializer.save()
#                     response = Response(serializer.data, status = status.HTTP_201_CREATED)
#                 response = Response(serializer.data, status = status.HTTP_400_BAD_REQUEST)
#             except utils.IntegrityError as e:
#                 if 'PRIMARY KEY constraint' in str(e):
#                     response = Response(serializer.data, status=status.HTTP_304_NOT_MODIFIED)
#                 elif('FOREIGN KEY') in str(e):
#                     response = Response(serializer.data, status=status.HTTP_406_NOT_ACCEPTABLE)
#                 else:
#                     response = Response(serializer.data, status = status.HTTP_400_BAD_REQUEST)
#         elif request.method == 'PUT':
#             try:
#                 entry = Entry.objects.get(pk=request.data['id'])
#                 serializer = EntrySerializer(instance=entry, data=request.data)
#                 if serializer.is_valid():
#                     serializer.save()
#                     return(Response(serializer.data, status=status.HTTP_202_ACCEPTED))
#                 else: 
#                     return(Response(serializer.data, status= status.HTTP_400_BAD_REQUEST))
#             except Entry.DoesNotExist:
#                 response = Response(serializer.data, status=status.HTTP_203_NON_AUTHORITATIVE_INFORMATION)
#             except utils.IntegrityError as e:
#                 if('FOREIGN KEY') in str(e):
#                     response = Response(serializer.data, status=status.HTTP_406_NOT_ACCEPTABLE)
#                 else:
#                     response = Response(serializer.data, status = status.HTTP_400_BAD_REQUEST)
#         elif request.method == 'GET':
#             entry = Entry.objects.all()
#             serializer = EntrySerializer(entry, many=True)
#             response = Response(serializer.data, status= status.HTTP_200_OK)
#         elif request.method == 'DELETE':
#             try:
#                 entry = Entry.objects.get(pk=request['id'])
#                 entry.delete()
#                 response = Response(data = None, status=status.HTTP_200_OK)
#             except Entry.DoesNotExist:
#                 response = Response(data=None, status= status.HTTP_204_NO_CONTENT)
#         else:
#             response = Response(data=None, status=status.HTTP_405_METHOD_NOT_ALLOWED)
#     # else:
#     #     response = Response(data=None, status = status.HTTP_403_FORBIDDEN)

# @api_view(['GET', 'POST', 'PUT', 'DELETE'])
# def getTagsFor(request: HttpRequest, format = None):
#     # signature = request.headers.get('X-Clockify-Signature') # or wherever the signing secret is held 
#     # payload = request.body
#     # secret = b'' # input signing secret here 
#     # auth = hmac.compare_digest(secret,payload,hashlib.sha256).hexdigest()
#     # if hmac.compare_digest(auth, signature):   
#         if request.method == 'POST':
#             try:
#                 serializer = TagsForSerializer(data = request.data)
#                 if serializer.is_valid():
#                     # # print(serializer.data)
#                     serializer.save()
#                     response = Response(serializer.data, status = status.HTTP_201_CREATED)
#                 response = Response(serializer.data, status = status.HTTP_400_BAD_REQUEST)
#             except utils.IntegrityError as e:
#                 if 'PRIMARY KEY constraint' in str(e):
#                     response = Response(serializer.data, status=status.HTTP_304_NOT_MODIFIED)
#                 elif('FOREIGN KEY') in str(e):
#                     response = Response(serializer.data, status=status.HTTP_406_NOT_ACCEPTABLE)
#                 else:
#                     response = Response(serializer.data, status = status.HTTP_400_BAD_REQUEST)
#         elif request.method == 'PUT':
#             try:
#                 tags = Tagsfor.objects.get(pk=request.data['id'])
#                 serializer = TagsForSerializer(instance=tags, data=request.data)
#                 if serializer.is_valid():
#                     serializer.save()
#                     return(Response(serializer.data, status=status.HTTP_202_ACCEPTED))
#                 else: 
#                     return(Response(serializer.data, status= status.HTTP_400_BAD_REQUEST))
#             except Tagsfor.DoesNotExist:
#                 response = Response(serializer.data, status=status.HTTP_203_NON_AUTHORITATIVE_INFORMATION)
#             except utils.IntegrityError as e:
#                 if('FOREIGN KEY') in str(e):
#                     response = Response(serializer.data, status=status.HTTP_406_NOT_ACCEPTABLE)
#                 else:
#                     response = Response(serializer.data, status = status.HTTP_400_BAD_REQUEST)
#         elif request.method == 'GET':
#             tags = Tagsfor.objects.all()
#             serializer = TagsForSerializer(tags, many=True)
#             response = Response(serializer.data, status= status.HTTP_200_OK)
#         elif request.method == 'DELETE':
#             try:
#                 tags = Tagsfor.objects.get(pk=request['id'])
#                 tags.delete()
#                 response = Response(data = None, status=status.HTTP_200_OK)
#             except Tagsfor.DoesNotExist:
#                 response = Response(data=None, status= status.HTTP_204_NO_CONTENT)
#         else:
#             response = Response(data=None, status=status.HTTP_405_METHOD_NOT_ALLOWED)
#     # else:
#     #     response = Response(data=None, status = status.HTTP_403_FORBIDDEN)
# '''
# @api_view(['GET', 'POST', 'PUT', 'DELETE'])
# def getTimeOffPolicies(request: HttpRequest, format = None):
#     # signature = request.headers.get('X-Clockify-Signature') # or wherever the signing secret is held 
#     # payload = request.body
#     # secret = b'' # input signing secret here 
#     # auth = hmac.compare_digest(secret,payload,hashlib.sha256).hexdigest()
#     # if hmac.compare_digest(auth, signature):   
#         if request.method == 'POST' or request.method == 'GET':
#             stat = QuickBackupV2.PolicyEvent()
#             logging.info(f'{get_current_time()} - Policy Event: Add Policy')
#             if stat:
#                 return Response(data='Check logs @: https://hpclockifyapi.azurewebsites.net/', status=status.HTTP_200_OK)
#             else: return Response(data='Check logs @: https://hpclockifyapi.azurewebsites.net/', status=status.HTTP_400_BAD_REQUEST)
#         else:
#             response = Response(data=None, status = status.HTTP_403_FORBIDDEN)
#             return response          
#         ''' 
#         elif request.method == 'PUT':
#             try:
#                 policy = Timeoffpolicies.objects.get(pk=request.data['id'])
#                 serializer = TimeOffPoliciesSerializer(instance=policy, data=request.data)
#                 if serializer.is_valid():
#                     serializer.save()
#                     return(Response(serializer.data, status=status.HTTP_202_ACCEPTED))
#                 else: 
#                     return(Response(serializer.data, status= status.HTTP_400_BAD_REQUEST))
#             except Timeoffpolicies.DoesNotExist:
#                 response = Response(serializer.data, status=status.HTTP_203_NON_AUTHORITATIVE_INFORMATION)
#             except utils.IntegrityError as e:
#                 if('FOREIGN KEY') in str(e):
#                     response = Response(serializer.data, status=status.HTTP_406_NOT_ACCEPTABLE)
#                 else:
#                     response = Response(serializer.data, status = status.HTTP_400_BAD_REQUEST)
#         elif request.method == 'GET':
#             policy = Timeoffpolicies.objects.all()
#             serializer = TimeOffPoliciesSerializer(policy, many=True)
#             response = Response(serializer.data, status= status.HTTP_200_OK)
#         elif request.method == 'DELETE':
#             try:
#                 policy = Timeoffpolicies.objects.get(pk=request['id'])
#                 policy.delete()
#                 response = Response(data = None, status=status.HTTP_200_OK)
#             except Timeoffpolicies.DoesNotExist:
#                 response = Response(data=None, status= status.HTTP_204_NO_CONTENT)
#         else:
#             response = Response(data=None, status=status.HTTP_405_METHOD_NOT_ALLOWED)
#     # else:
#     #     response = Response(data=None, status = status.HTTP_403_FORBIDDEN)
#         '''

# @api_view(['GET', 'POST', 'PUT', 'DELETE'])
# def getTimeOffRequests(request: HttpRequest, format = None):
#     # signature = request.headers.get('X-Clockify-Signature') # or wherever the signing secret is held 
#     # payload = request.body
#     # secret = b'' # input signing secret here 
#     # auth = hmac.compare_digest(secret,payload,hashlib.sha256).hexdigest()
#     # if hmac.compare_digest(auth, signature):   
#         if request.method == 'POST' or request.method == 'GET':
#             stat = QuickBackupV2.TimeOffEvent()
#             logging.info(f'{get_current_time()} - Time Off  Event: Add Time Off')
#             if stat:
#                 return Response(data='Check logs @: https://hpclockifyapi.azurewebsites.net/', status=status.HTTP_200_OK)
#             else: return Response(data='Check logs @: https://hpclockifyapi.azurewebsites.net/', status=status.HTTP_400_BAD_REQUEST)
#         else:
#             response = Response(data=None, status = status.HTTP_403_FORBIDDEN)
#             return response
#         '''
#         elif request.method == 'PUT':
#             try:
#                 timeOff = Timeoffrequests.objects.get(pk=request.data['id'])
#                 serializer = TimeOffRequestsSerializer(instance=timeOff, data=request.data)
#                 if serializer.is_valid():
#                     serializer.save()
#                     return(Response(serializer.data, status=status.HTTP_202_ACCEPTED))
#                 else: 
#                     return(Response(serializer.data, status= status.HTTP_400_BAD_REQUEST))
#             except Timeoffrequests.DoesNotExist:
#                 response = Response(serializer.data, status=status.HTTP_203_NON_AUTHORITATIVE_INFORMATION)
#             except utils.IntegrityError as e:
#                 if('FOREIGN KEY') in str(e):
#                     response = Response(serializer.data, status=status.HTTP_406_NOT_ACCEPTABLE)
#                 else:
#                     response = Response(serializer.data, status = status.HTTP_400_BAD_REQUEST)
#         elif request.method == 'GET':
#             timeOff = Timeoffrequests.objects.all()
#             serializer = TimeOffRequestsSerializer(timeOff, many=True)
#             response = Response(serializer.data, status= status.HTTP_200_OK)
#         elif request.method == 'DELETE':
#             try:
#                 timeOff = Timeoffrequests.objects.get(pk=request['id'])
#                 timeOff.delete()
#                 response = Response(data = None, status=status.HTTP_200_OK)
#             except Timeoffrequests.DoesNotExist:
#                 response = Response(data=None, status= status.HTTP_204_NO_CONTENT)
#         else:
#             response = Response(data=None, status=status.HTTP_405_METHOD_NOT_ALLOWED)
#     # else:
#     #     response = Response(data=None, status = status.HTTP_403_FORBIDDEN)
#         '''

# '''
# @api_view(['GET', 'POST', 'PUT', 'DELETE'])
# def getCalendars(request: HttpRequest, format = None):
#     # signature = request.headers.get('X-Clockify-Signature') # or wherever the signing secret is held 
#     # payload = request.body
#     # secret = b'' # input signing secret here 
#     # auth = hmac.compare_digest(secret,payload,hashlib.sha256).hexdigest()
#     # if hmac.compare_digest(auth, signature):   
#         if request.method == 'POST':
#             try:
#                 serializer = CalendarSerializer(data = request.data)
#                 if serializer.is_valid():
#                     # # print(serializer.data)
#                     serializer.save()
#                     response = Response(serializer.data, status = status.HTTP_201_CREATED)
#                 response = Response(serializer.data, status = status.HTTP_400_BAD_REQUEST)
#             except utils.IntegrityError as e:
#                 if 'PRIMARY KEY constraint' in str(e):
#                     response = Response(serializer.data, status=status.HTTP_304_NOT_MODIFIED)
#                 elif('FOREIGN KEY') in str(e):
#                     response = Response(serializer.data, status=status.HTTP_406_NOT_ACCEPTABLE)
#                 else:
#                     response = Response(serializer.data, status = status.HTTP_400_BAD_REQUEST)
#         elif request.method == 'PUT':
#             try:
#                 day = Calendar.objects.get(pk=request.data['id'])
#                 serializer = CalendarSerializer(instance=day, data=request.data)
#                 if serializer.is_valid():
#                     serializer.save()
#                     return(Response(serializer.data, status=status.HTTP_202_ACCEPTED))
#                 else: 
#                     return(Response(serializer.data, status= status.HTTP_400_BAD_REQUEST))
#             except Calendar.DoesNotExist:
#                 response = Response(serializer.data, status=status.HTTP_203_NON_AUTHORITATIVE_INFORMATION)
#             except utils.IntegrityError as e:
#                 if('FOREIGN KEY') in str(e):
#                     response = Response(serializer.data, status=status.HTTP_406_NOT_ACCEPTABLE)
#                 else:
#                     response = Response(serializer.data, status = status.HTTP_400_BAD_REQUEST)
#         elif request.method == 'GET':
#             day = Calendar.objects.all()
#             serializer = CalendarSerializer(day, many=True)
#             response = Response(serializer.data, status= status.HTTP_200_OK)
#         elif request.method == 'DELETE':
#             try:
#                 day = Calendar.objects.get(pk=request['id'])
#                 day.delete()
#                 response = Response(data = None, status=status.HTTP_200_OK)
#             except Calendar.DoesNotExist:
#                 response = Response(data=None, status= status.HTTP_204_NO_CONTENT)
#         else:
#             response = Response(data=None, status=status.HTTP_405_METHOD_NOT_ALLOWED)
#     # else:
#     #     response = Response(data=None, status = status.HTTP_403_FORBIDDEN)

# @api_view(['GET', 'POST', 'PUT', 'DELETE'])
# def getUserGroups(request: HttpRequest, format = None):
#     # signature = request.headers.get('X-Clockify-Signature') # or wherever the signing secret is held 
#     # payload = request.body
#     # secret = b'' # input signing secret here 
#     # auth = hmac.compare_digest(secret,payload,hashlib.sha256).hexdigest()
#     # if hmac.compare_digest(auth, signature):   
#         if request.method == 'POST':
#             try:
#                 serializer = UserGroupsSerializer(data = request.data)
#                 if serializer.is_valid():
#                     # # print(serializer.data)
#                     serializer.save()
#                     response = Response(serializer.data, status = status.HTTP_201_CREATED)
#                 response = Response(serializer.data, status = status.HTTP_400_BAD_REQUEST)
#             except utils.IntegrityError as e:
#                 if 'PRIMARY KEY constraint' in str(e):
#                     response = Response(serializer.data, status=status.HTTP_304_NOT_MODIFIED)
#                 elif('FOREIGN KEY') in str(e):
#                     response = Response(serializer.data, status=status.HTTP_406_NOT_ACCEPTABLE)
#                 else:
#                     response = Response(serializer.data, status = status.HTTP_400_BAD_REQUEST)
#         elif request.method == 'PUT':
#             try:
#                 group = Usergroups.objects.get(pk=request.data['id'])
#                 serializer = UserGroupsSerializer(instance=group, data=request.data)
#                 if serializer.is_valid():
#                     serializer.save()
#                     return(Response(serializer.data, status=status.HTTP_202_ACCEPTED))
#                 else: 
#                     return(Response(serializer.data, status= status.HTTP_400_BAD_REQUEST))
#             except Usergroups.DoesNotExist:
#                 response = Response(serializer.data, status=status.HTTP_203_NON_AUTHORITATIVE_INFORMATION)
#             except utils.IntegrityError as e:
#                 if('FOREIGN KEY') in str(e):
#                     response = Response(serializer.data, status=status.HTTP_406_NOT_ACCEPTABLE)
#                 else:
#                     response = Response(serializer.data, status = status.HTTP_400_BAD_REQUEST)
#         elif request.method == 'GET':
#             group = Usergroups.objects.all()
#             serializer = UserGroupsSerializer(group, many=True)
#             response = Response(serializer.data, status= status.HTTP_200_OK)
#         elif request.method == 'DELETE':
#             try:
#                 group = Usergroups.objects.get(pk=request['id'])
#                 group.delete()
#                 response = Response(data = None, status=status.HTTP_200_OK)
#             except Usergroups.DoesNotExist:
#                 response = Response(data=None, status= status.HTTP_204_NO_CONTENT)
#         else:
#             response = Response(data=None, status=status.HTTP_405_METHOD_NOT_ALLOWED)
#     # else:
#     #     response = Response(data=None, status = status.HTTP_403_FORBIDDEN)

# @api_view(['GET', 'POST', 'PUT', 'DELETE'])
# def getGroupMembership(request: HttpRequest, format = None):
#     # signature = request.headers.get('X-Clockify-Signature') # or wherever the signing secret is held 
#     # payload = request.body
#     # secret = b'' # input signing secret here 
#     # auth = hmac.compare_digest(secret,payload,hashlib.sha256).hexdigest()
#     # if hmac.compare_digest(auth, signature):   
#         if request.method == 'POST':
#             try:
#                 serializer = GroupMembershipSerializer(data = request.data)
#                 if serializer.is_valid():
#                     # # print(serializer.data)
#                     serializer.save()
#                     response = Response(serializer.data, status = status.HTTP_201_CREATED)
#                 response = Response(serializer.data, status = status.HTTP_400_BAD_REQUEST)
#             except utils.IntegrityError as e:
#                 if 'PRIMARY KEY constraint' in str(e):
#                     response = Response(serializer.data, status=status.HTTP_304_NOT_MODIFIED)
#                 elif('FOREIGN KEY') in str(e):
#                     response = Response(serializer.data, status=status.HTTP_406_NOT_ACCEPTABLE)
#                 else:
#                     response = Response(serializer.data, status = status.HTTP_400_BAD_REQUEST)
#         elif request.method == 'PUT':
#             try:
#                 member = Groupmembership.objects.get(pk=request.data['id'])
#                 serializer = GroupMembershipSerializer(instance=member, data=request.data)
#                 if serializer.is_valid():
#                     serializer.save()
#                     return(Response(serializer.data, status=status.HTTP_202_ACCEPTED))
#                 else: 
#                     return(Response(serializer.data, status= status.HTTP_400_BAD_REQUEST))
#             except Groupmembership.DoesNotExist:
#                 response = Response(serializer.data, status=status.HTTP_203_NON_AUTHORITATIVE_INFORMATION)
#             except utils.IntegrityError as e:
#                 if('FOREIGN KEY') in str(e):
#                     response = Response(serializer.data, status=status.HTTP_406_NOT_ACCEPTABLE)
#                 else:
#                     response = Response(serializer.data, status = status.HTTP_400_BAD_REQUEST)
#         elif request.method == 'GET':
#             member = Groupmembership.objects.all()
#             serializer = GroupMembershipSerializer(member, many=True)
#             response = Response(serializer.data, status= status.HTTP_200_OK)
#         elif request.method == 'DELETE':
#             try:
#                 member = Groupmembership.objects.get(pk=request['id'])
#                 member.delete()
#                 response = Response(data = None, status=status.HTTP_200_OK)
#             except Groupmembership.DoesNotExist:
#                 response = Response(data=None, status= status.HTTP_204_NO_CONTENT)
#         else:
#             response = Response(data=None, status=status.HTTP_405_METHOD_NOT_ALLOWED)
#     # else:
#     #     response = Response(data=None, status = status.HTTP_403_FORBIDDEN)

# def getHolidays(request: HttpRequest, format = None):
#     holidays = Holidays.objects.all()
#     serializer = HolidaysSerializer(holidays, many=True)
#     response = Response(serializer.data)
# '''