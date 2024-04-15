from django.http import HttpRequest
from django.db import transaction
import json
from .models import (
    Workspace,
    Client,
    Employeeuser,
    Timesheet,
    Project,
    Entry,
    Tagsfor,
    Timeoffpolicies,
    Timeoffrequests,
    Calendar,
    Holidays,
    Usergroups,
    Groupmembership,
)
from django.db import utils
from .serializers import (
    WorkspaceSerializer,
    ClientSerializer,
    EmployeeUserSerializer,
    TimeSheetSerializer,
    ProjectSerializer,
    EntrySerializer,
    TagsForSerializer,
    TimeOffPoliciesSerializer,
    TimeOffRequestsSerializer,
    CalendarSerializer,
    HolidaysSerializer,
    UserGroupsSerializer,
    GroupMembershipSerializer,
)
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import pyodbc
from . import ClockifyPull

from django.http import HttpResponse
import os
from . import settings
from . import QuickBackup
import logging
from rest_framework.exceptions import ValidationError
@api_view(['GET'])
def quickBackup(request: HttpRequest):
    result = QuickBackup.main()
    response = Response(data = result, status=status.HTTP_200_OK)

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
    
@api_view(['GET', 'PUT', 'POST', 'DELETE'])
def getClients(request: HttpRequest, format = None):
    # signature = request.headers.get('X-Clockify-Signature') # or wherever the signing secret is held 
    # payload = request.body
    # secret = b'' # input signing secret here 
    # auth = hmac.compare_digest(secret,payload,hashlib.sha256).hexdigest()
    # if hmac.compare_digest(auth, signature):   
        if request.method == 'GET':
            clients = Client.objects.all()
            serializer = ClientSerializer(clients, many=True)
            response = Response(serializer.data )
        elif request.method == 'PUT':
            try: 
                client = Client.objects.get(pk=request['id'])
                serializer = ClientSerializer(instance= client, data = request.data)
                if serializer.is_valid():
                    serializer.save()
                    response = Response( data= serializer.data, status= status.HTTP_202_ACCEPTED)
                return(Response(serializer.data, status= status.HTTP_400_BAD_REQUEST))
            except Client.DoesNotExist:
                response = Response(data= serializer.data, status= status.HTTP_203_NON_AUTHORITATIVE_INFORMATION)
            except utils.IntegrityError as e:
                if 'PRIMARY KEY constraint' in str(e): 
                    response = Response(serializer.data, status=status.HTTP_304_NOT_MODIFIED)
                elif('FOREIGN KEY') in str(e): # maybe include calls to update and try again in the future 
                    response = Response(serializer.data, status=status.HTTP_406_NOT_ACCEPTABLE)
                else:
                    response = Response(serializer.data, status = status.HTTP_400_BAD_REQUEST) 
        elif request.method == 'POST':
            serializer = ClientSerializer(data = request.data)
            if serializer.is_valid():
                serializer.save()
                response = Response( data = serializer.data, status = status.HTTP_201_CREATED)
            response = Response( data= serializer.data, status = status.HTTP_400_BAD_REQUEST)
        elif request.method == 'DELETE':
            try:
                client = Client.objects.get(pk=request['id'])
                client.delete()
                response = Response(data = None, status=status.HTTP_200_OK)
            except Client.DoesNotExist:
                response = Response(data=None, status= status.HTTP_204_NO_CONTENT)
        else:
            response = Response(data=None, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    # else:
    #     response = Response(data=None, status = status.HTTP_403_FORBIDDEN)

@api_view(['GET', 'POST', 'PUT', 'DELETE'])
def getEmployeeUsers(request: HttpRequest, format = None):
    # signature = request.headers.get('X-Clockify-Signature') # or wherever the signing secret is held 
    # payload = request.body
    # secret = b'' # input signing secret here 
    # auth = hmac.compare_digest(secret,payload,hashlib.sha256).hexdigest()
    # if hmac.compare_digest(auth, signature):   
        if request.method == 'GET':
            user = Employeeuser.objects.all()
            serializer = EmployeeUserSerializer(user, many=True)
            response = Response(serializer.data )
        elif request.method == 'PUT':
            try: 
                user = Employeeuser.objects.get(pk=request['id'])
                serializer = EmployeeUserSerializer(instance= user, data = request.data)
                if serializer.is_valid():
                    serializer.save()
                    response = Response( data= serializer.data, status= status.HTTP_202_ACCEPTED)
                return(Response(serializer.data, status= status.HTTP_400_BAD_REQUEST))
            except Employeeuser.DoesNotExist:
                response = Response(data= serializer.data, status= status.HTTP_203_NON_AUTHORITATIVE_INFORMATION)
            except utils.IntegrityError as e:
                if 'PRIMARY KEY constraint' in str(e): 
                    response = Response(serializer.data, status=status.HTTP_304_NOT_MODIFIED)
                elif('FOREIGN KEY') in str(e): # maybe include calls to update and try again in the future 
                    response = Response(serializer.data, status=status.HTTP_406_NOT_ACCEPTABLE)
                else:
                    response = Response(serializer.data, status = status.HTTP_400_BAD_REQUEST) 
        elif request.method == 'POST':
            serializer = EmployeeUserSerializer(data = request.data)
            if serializer.is_valid():
                serializer.save()
                response = Response( data = serializer.data, status = status.HTTP_201_CREATED)
            response = Response( data= serializer.data, status = status.HTTP_400_BAD_REQUEST)
        elif request.method == 'DELETE':
            try:
                user = Employeeuser.objects.get(pk=request['id'])
                user.delete()
                response = Response(data = None, status=status.HTTP_200_OK)
            except Employeeuser.DoesNotExist:
                response = Response(data=None, status= status.HTTP_204_NO_CONTENT)
        else:
            response = Response(data=None, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    # else:
    #     response = Response(data=None, status = status.HTTP_403_FORBIDDEN)
'''
@api_view(['GET'])
def view_log(request):
    log_file_path = os.path.join(settings.LOGS_DIR, 'ServerLog.log')  # Update with the path to your logging file
    if os.path.exists(log_file_path):
        with open(log_file_path, 'r') as file:
            # Read all lines from the file
            lines = file.readlines()
            # Extract the last 1000 lines
            last_1000_lines = lines[-1000:]
            # Reverse the order of the lines
            reversed_lines = reversed(last_1000_lines)
            # Join the lines into a single string
            log_contents = ''.join(reversed_lines)
        return HttpResponse(log_contents, content_type='text/plain')
    else:
        return HttpResponse('Logging file not found', status=404)
    
def updateTags(entrySerilizer: EntrySerializer, request, timeId, workspaceId):
    logging.info(f'updateTags Function called')
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
        i += 1
        if serializer.is_valid():
            serializer.save()
            serializers.append(serializer.validated_data)
        else: 
            # print (serializer.validated_data)
            raise ValidationError(serializer.errors)
    response = Response(data= serializers, status = status.HTTP_202_ACCEPTED)
    logging.info(response)
    return response

def updateEntries(request, timeSerializer):
    logging.info('updateEntreis Function called')
    key = ClockifyPull.getApiKey()
    timeId = timeSerializer.validated_data['id']
    # print (timeId)
    workspaceId = timeSerializer.validated_data['workspaceId']
    stat = timeSerializer.validated_data['status']['state']
    if stat == 'APPROVED':
        entries = ClockifyPull.getEntryForApproval(workspaceId, key, timeId, stat, 1)
        # print(json.dumps(entries, indent = 4))
        i = 0
        serializers = []
        while i < len(entries):
            try: 
                approvalID = entries[i]['approvalRequestId'] if entries[i]['approvalRequestId'] is not None else timeId
                entry = Entry.objects.get(id = entries[i]['id'], workspace = 'workspaceId', time_sheet = approvalID)
                serializer = EntrySerializer(data=entries[i], instance=entry, context = {'workspaceId': workspaceId,'approvalRequestId': timeId})
                i += 1
            except Entry.DoesNotExist:
                serializer = EntrySerializer(data=entries[i], context = {'workspaceId': workspaceId,'approvalRequestId': timeId})
                i += 1
            if serializer.is_valid():
                serializer.save()
                tagResponse = updateTags(serializer, request, timeId, workspaceId)
                serializers.append(serializer.validated_data)
            else: raise ValidationError(serializer.errors)
        response = Response(data = {'entry': serializers}, status = status.HTTP_202_ACCEPTED)
        logging.info(response)
        return response
    else:
        response = Response(data={'entry': 'No Entries'}, status=status.HTTP_200_OK)
        logging.info(response)
        return response

@api_view(['POST'])
def updateTimesheet(request:HttpRequest):
    try: 
        with transaction.atomic():
            timesheet = Timesheet.objects.get(pk=request.data['id'])
            serializer = TimeSheetSerializer(instance= timesheet, data = request.data)
            if serializer.is_valid():
                serializer.save()
                entryResponse = updateEntries(request, serializer)
                response = Response(data ={
                                        'timesheet':serializer.validated_data, 
                                        'entry': entryResponse.data 
                                    }, status = status.HTTP_202_ACCEPTED)
                logging.info(response)
                return response
            else: 
                response = Response(data=serializer.error_messages, status=status.HTTP_400_BAD_REQUEST)
                logging.error(response)
                return response
    except Timesheet.DoesNotExist:
        response = Response(data={'Message': 'Timesheet Does not exist to be updated'}, status= status.HTTP_304_NOT_MODIFIED)
        logging.error(response)
        return response
    except Exception as e:
        transaction.rollback()
        response = Response(data= {'Message': str(e)}, status= status.HTTP_400_BAD_REQUEST)
        logging.error(response)
        return response
    
def loadTags(entrySerilizer: EntrySerializer, request: HttpRequest = None, timeId: str = None, workspaceId: str = None):
    serializers = []
    if request.method == 'POST': # called from Entry< Put >
        try:
            # print (entrySerilizer)
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
            except Tagsfor.DoesNotExist: 
                # print('No existing taggs')
                pass
                # Find new tags to create
            i = 0
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
                i += 1
                if serializer.is_valid():
                    serializer.save()
                    serializers.append(serializer.validated_data)
                else: 
                    print (serializer.validated_data)
                    response = Response(data = [serializer.errors], status = status.HTTP_400_BAD_REQUEST)
            response = Response(data= serializers, status = status.HTTP_202_ACCEPTED)
            logging.info(response)
            return response
        except Exception as e:
            print(e)
            response = Response(data=[str(e)], status= status.HTTP_400_BAD_REQUEST) 
            logging.error(response)
            return response

def loadEntries( request: HttpRequest, timeSerilizer: TimeSheetSerializer = None, ):
    key = ClockifyPull.getApiKey()
    timeId = timeSerilizer.validated_data['id']
    # print (timeId)
    workspaceId = timeSerilizer.validated_data['workspaceId']
    stat = timeSerilizer.validated_data['status']['state']
    entries = ClockifyPull.getEntryForApproval(workspaceId, key, timeId, stat, 1)
    if len(entries) >0:
        print (json.dumps(entries, indent=4))
        if request.method == 'POST':
            serializer = EntrySerializer(data = entries,  context = {'workspaceId': workspaceId,'approvalRequestId': timeId}, many= True)
            if serializer.is_valid():
                serializer.save()
                tagResponse = loadTags(serializer, request, timeId, workspaceId)
                response = Response(data = {'entryS':serializer.validated_data, 'tagResponse': tagResponse }, status=status.HTTP_201_CREATED)
                logging.info(response)
                return response
            else: 
                response = Response(data= {'entryS': serializer.errors}, status = status.HTTP_400_BAD_REQUEST)
                logging.error(response)
                return response
        else:
            response = Response(data= 'Invalid method', status = status.HTTP_400_BAD_REQUEST)
            logging.error(response)
            return response 
    else: 
        response = Response(data= {'entryS':'No Entries or timesheet is pending'}, status=status.HTTP_202_ACCEPTED) 
        logging.info(response)
        return response

@api_view([ 'POST'])
def getTimeSheets(request: HttpRequest, format = None):
        logging.info(request.method)
        '''
        # signature = request.headers.get('X-Clockify-Signature') # or wherever the signing secret is held 
        # payload = request.body
        # secret = b'' # input signing secret here 
        # auth = hmac.compare_digest(secret,payload,hashlib.sha256).hexdigest()
        # if hmac.compare_digest(auth, signature):   
            if request.method == 'GET':
                timesheet = Timesheet.objects.all()
                serializer = TimeSheetSerializer(timesheet, many=True)
                response = Response(serializer.data )
            elif request.method == 'PUT':
                try: 
                    timesheet = Timesheet.objects.get(pk=request.data['id'])
                    serializer = TimeSheetSerializer(instance= timesheet, data = request.data)
                    if serializer.is_valid():
                        serializer.save() 
                        entryReponse = loadEntries(request, serializer)
                        entryData = entryReponse.data
                        # print(entryData)
                        if entryReponse.status_code >= 200 and entryReponse.status_code <= 299: # entries were saved properly
                            tagResponse = entryData.get('tagResponse')
                            if tagResponse is not None and  tagResponse.status_code >=200 and tagResponse.status_code <=299:
                                return( Response( 
                                    data ={
                                        'timesheet':serializer.validated_data, 
                                        'entry': entryData.get('entryS'),
                                        'tag': tagResponse.data
                                    }, status = status.HTTP_202_ACCEPTED))
                            else: response = Response(data= entryData, status =status.HTTP_207_MULTI_STATUS)
                        else: Response(data= entryData, status= status.HTTP_207_MULTI_STATUS)
                    return(Response(serializer.errors, status= status.HTTP_400_BAD_REQUEST))
                except Timesheet.DoesNotExist:
                    response = Response('Timesheet Does Not Exists', status= status.HTTP_203_NON_AUTHORITATIVE_INFORMATION)
                except utils.IntegrityError as e:
                    if 'PRIMARY KEY constraint' in str(e): 
                        # print(str(e))
                        response = Response(data ={
                                        'timesheet':serializer.validated_data, 
                                        'entry': entryData.get('entryS').validated_data,
                    
                                        'tag': tagResponse.data.validated_data 
                                    }, status=status.HTTP_304_NOT_MODIFIED)
                    elif('FOREIGN KEY') in str(e): # maybe include calls to update and try again in the future 
                        response = Response(serializer.data, status=status.HTTP_406_NOT_ACCEPTABLE)
                    else:
                        response = Response(serializer.data, status = status.HTTP_400_BAD_REQUEST)    
        '''
        if request.method == 'POST':
            try:
                data = request.data
                serializer = TimeSheetSerializer(data= data)
                if serializer.is_valid():
                    serializer.save()
                    # store entries and then return 
                    '''
                    entryReponse = loadEntries(request, serializer)
                    entryData = entryReponse.data
                    if entryReponse.status_code >= 200 and entryReponse.status_code <= 299: # entries were saved properly
                        tagResponse = entryData.get('tagResponse')
                        if tagResponse is not None and tagResponse.status_code >=200 and tagResponse.status_code <=299:
                            response = Response( 
                                data ={
                                    'timesheet':serializer.validated_data, 
                                    'entry': entryData.get('entryS'),
                                    'tag': tagResponse.data 
                                }, status = status.HTTP_201_CREATED)
                            logging.info(response)
                            return response
                        else: 
                            response = Response(data= entryData, status =status.HTTP_201_CREATED)
                            logging.info(response)
                            return response
                    else: 
                        response = Response(data= {'entry_data': entryReponse.data}, status= status.HTTP_201_CREATED)
                    '''
                    response = Response( data= serializer.validated_data, status = status.HTTP_201_CREATED)
                    logging.info(response)
                    return response
                else:
                    response = Response(data= serializer.error_messages, status=status.HTTP_400_BAD_REQUEST)
                    logging.error(response)
                    return response
            except utils.IntegrityError as e:
                if 'PRIMARY KEY constraint' in str(e): 
                    response = Response(data={'Constraint':  str(e)}, status=status.HTTP_304_NOT_MODIFIED)
                    logging.error(response)
                    return response
                elif('FOREIGN KEY') in str(e): # maybe include calls to update and try again in the future 
                    response = Response(data=str(e), status=status.HTTP_406_NOT_ACCEPTABLE)
                    logging.error(response)
                    return response
                else:
                    response = Response(data=str(e), status = status.HTTP_400_BAD_REQUEST) 
                    logging.error(response)
                    return response
'''
        elif request.method == 'DELETE':
        try:
            timesheet = Timesheet.objects.get(pk=request['id'])
            timesheet.delete()
            response = Response(data = None, status=status.HTTP_200_OK)
        except Timesheet.DoesNotExist:
            response = Response(data=None, status= status.HTTP_204_NO_CONTENT)
    else:
        response = Response(data=None, status=status.HTTP_405_METHOD_NOT_ALLOWED)
# else:
#     response = Response(data=None, status = status.HTTP_403_FORBIDDEN)
'''
'''
@api_view(['GET', 'POST', 'PUT', 'DELETE'])
def getProjects(request: HttpRequest, format = None):
    # signature = request.headers.get('X-Clockify-Signature') # or wherever the signing secret is held 
    # payload = request.body
    # secret = b'' # input signing secret here 
    # auth = hmac.compare_digest(secret,payload,hashlib.sha256).hexdigest()
    # if hmac.compare_digest(auth, signature):   
        if request.method == 'POST':
            try:
                serializer = ProjectSerializer(data = request.data)
                if serializer.is_valid():
                    # # print(serializer.data)
                    serializer.save()
                    response = Response(serializer.data, status = status.HTTP_201_CREATED)
                response = Response(serializer.data, status = status.HTTP_400_BAD_REQUEST)
            except utils.IntegrityError as e:
                if 'PRIMARY KEY constraint' in str(e):
                    response = Response(serializer.data, status=status.HTTP_304_NOT_MODIFIED)
                elif('FOREIGN KEY') in str(e):
                    response = Response(serializer.data, status=status.HTTP_406_NOT_ACCEPTABLE)
                else:
                    response = Response(serializer.data, status = status.HTTP_400_BAD_REQUEST)
        elif request.method == 'PUT':
            try:
                project = Project.objects.get(pk=request.data['id'])
                serializer = ProjectSerializer(instance=project, data=request.data)
                if serializer.is_valid():
                    serializer.save()
                    return(Response(serializer.data, status=status.HTTP_202_ACCEPTED))
                else: 
                    return(Response(serializer.data, status= status.HTTP_400_BAD_REQUEST))
            except Project.DoesNotExist:
                response = Response(serializer.data, status=status.HTTP_203_NON_AUTHORITATIVE_INFORMATION)
            except utils.IntegrityError as e:
                if('FOREIGN KEY') in str(e):
                    response = Response(serializer.data, status=status.HTTP_406_NOT_ACCEPTABLE)
                else:
                    response = Response(serializer.data, status = status.HTTP_400_BAD_REQUEST)
        elif request.method == 'GET':
            projects = Project.objects.all()
            serializer = ProjectSerializer(projects, many=True)
            response = Response(serializer.data, status= status.HTTP_200_OK)
        elif request.method == 'DELETE':
            try:
                project = Project.objects.get(pk=request['id'])
                project.delete()
                response = Response(data = None, status=status.HTTP_200_OK)
            except Project.DoesNotExist:
                response = Response(data=None, status= status.HTTP_204_NO_CONTENT)
        else:
            response = Response(data=None, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    # else:
    #     response = Response(data=None, status = status.HTTP_403_FORBIDDEN)
   
@api_view(['GET', 'POST', 'PUT', 'DELETE'])
def getEntries(request: HttpRequest, format = None):
    # signature = request.headers.get('X-Clockify-Signature') # or wherever the signing secret is held 
    # payload = request.body
    # secret = b'' # input signing secret here 
    # auth = hmac.compare_digest(secret,payload,hashlib.sha256).hexdigest()
    # if hmac.compare_digest(auth, signature):   
        if request.method == 'POST':
            try:
                serializer = EntrySerializer(data = request.data)
                if serializer.is_valid():
                    # # print(serializer.data)
                    serializer.save()
                    response = Response(serializer.data, status = status.HTTP_201_CREATED)
                response = Response(serializer.data, status = status.HTTP_400_BAD_REQUEST)
            except utils.IntegrityError as e:
                if 'PRIMARY KEY constraint' in str(e):
                    response = Response(serializer.data, status=status.HTTP_304_NOT_MODIFIED)
                elif('FOREIGN KEY') in str(e):
                    response = Response(serializer.data, status=status.HTTP_406_NOT_ACCEPTABLE)
                else:
                    response = Response(serializer.data, status = status.HTTP_400_BAD_REQUEST)
        elif request.method == 'PUT':
            try:
                entry = Entry.objects.get(pk=request.data['id'])
                serializer = EntrySerializer(instance=entry, data=request.data)
                if serializer.is_valid():
                    serializer.save()
                    return(Response(serializer.data, status=status.HTTP_202_ACCEPTED))
                else: 
                    return(Response(serializer.data, status= status.HTTP_400_BAD_REQUEST))
            except Entry.DoesNotExist:
                response = Response(serializer.data, status=status.HTTP_203_NON_AUTHORITATIVE_INFORMATION)
            except utils.IntegrityError as e:
                if('FOREIGN KEY') in str(e):
                    response = Response(serializer.data, status=status.HTTP_406_NOT_ACCEPTABLE)
                else:
                    response = Response(serializer.data, status = status.HTTP_400_BAD_REQUEST)
        elif request.method == 'GET':
            entry = Entry.objects.all()
            serializer = EntrySerializer(entry, many=True)
            response = Response(serializer.data, status= status.HTTP_200_OK)
        elif request.method == 'DELETE':
            try:
                entry = Entry.objects.get(pk=request['id'])
                entry.delete()
                response = Response(data = None, status=status.HTTP_200_OK)
            except Entry.DoesNotExist:
                response = Response(data=None, status= status.HTTP_204_NO_CONTENT)
        else:
            response = Response(data=None, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    # else:
    #     response = Response(data=None, status = status.HTTP_403_FORBIDDEN)

@api_view(['GET', 'POST', 'PUT', 'DELETE'])
def getTagsFor(request: HttpRequest, format = None):
    # signature = request.headers.get('X-Clockify-Signature') # or wherever the signing secret is held 
    # payload = request.body
    # secret = b'' # input signing secret here 
    # auth = hmac.compare_digest(secret,payload,hashlib.sha256).hexdigest()
    # if hmac.compare_digest(auth, signature):   
        if request.method == 'POST':
            try:
                serializer = TagsForSerializer(data = request.data)
                if serializer.is_valid():
                    # # print(serializer.data)
                    serializer.save()
                    response = Response(serializer.data, status = status.HTTP_201_CREATED)
                response = Response(serializer.data, status = status.HTTP_400_BAD_REQUEST)
            except utils.IntegrityError as e:
                if 'PRIMARY KEY constraint' in str(e):
                    response = Response(serializer.data, status=status.HTTP_304_NOT_MODIFIED)
                elif('FOREIGN KEY') in str(e):
                    response = Response(serializer.data, status=status.HTTP_406_NOT_ACCEPTABLE)
                else:
                    response = Response(serializer.data, status = status.HTTP_400_BAD_REQUEST)
        elif request.method == 'PUT':
            try:
                tags = Tagsfor.objects.get(pk=request.data['id'])
                serializer = TagsForSerializer(instance=tags, data=request.data)
                if serializer.is_valid():
                    serializer.save()
                    return(Response(serializer.data, status=status.HTTP_202_ACCEPTED))
                else: 
                    return(Response(serializer.data, status= status.HTTP_400_BAD_REQUEST))
            except Tagsfor.DoesNotExist:
                response = Response(serializer.data, status=status.HTTP_203_NON_AUTHORITATIVE_INFORMATION)
            except utils.IntegrityError as e:
                if('FOREIGN KEY') in str(e):
                    response = Response(serializer.data, status=status.HTTP_406_NOT_ACCEPTABLE)
                else:
                    response = Response(serializer.data, status = status.HTTP_400_BAD_REQUEST)
        elif request.method == 'GET':
            tags = Tagsfor.objects.all()
            serializer = TagsForSerializer(tags, many=True)
            response = Response(serializer.data, status= status.HTTP_200_OK)
        elif request.method == 'DELETE':
            try:
                tags = Tagsfor.objects.get(pk=request['id'])
                tags.delete()
                response = Response(data = None, status=status.HTTP_200_OK)
            except Tagsfor.DoesNotExist:
                response = Response(data=None, status= status.HTTP_204_NO_CONTENT)
        else:
            response = Response(data=None, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    # else:
    #     response = Response(data=None, status = status.HTTP_403_FORBIDDEN)

@api_view(['GET', 'POST', 'PUT', 'DELETE'])
def getTimeOffPolicies(request: HttpRequest, format = None):
    # signature = request.headers.get('X-Clockify-Signature') # or wherever the signing secret is held 
    # payload = request.body
    # secret = b'' # input signing secret here 
    # auth = hmac.compare_digest(secret,payload,hashlib.sha256).hexdigest()
    # if hmac.compare_digest(auth, signature):   
        if request.method == 'POST':
            try:
                serializer = TimeOffPoliciesSerializer(data = request.data)
                if serializer.is_valid():
                    # # print(serializer.data)
                    serializer.save()
                    response = Response(serializer.data, status = status.HTTP_201_CREATED)
                response = Response(serializer.data, status = status.HTTP_400_BAD_REQUEST)
            except utils.IntegrityError as e:
                if 'PRIMARY KEY constraint' in str(e):
                    response = Response(serializer.data, status=status.HTTP_304_NOT_MODIFIED)
                elif('FOREIGN KEY') in str(e):
                    response = Response(serializer.data, status=status.HTTP_406_NOT_ACCEPTABLE)
                else:
                    response = Response(serializer.data, status = status.HTTP_400_BAD_REQUEST)
        elif request.method == 'PUT':
            try:
                policy = Timeoffpolicies.objects.get(pk=request.data['id'])
                serializer = TimeOffPoliciesSerializer(instance=policy, data=request.data)
                if serializer.is_valid():
                    serializer.save()
                    return(Response(serializer.data, status=status.HTTP_202_ACCEPTED))
                else: 
                    return(Response(serializer.data, status= status.HTTP_400_BAD_REQUEST))
            except Timeoffpolicies.DoesNotExist:
                response = Response(serializer.data, status=status.HTTP_203_NON_AUTHORITATIVE_INFORMATION)
            except utils.IntegrityError as e:
                if('FOREIGN KEY') in str(e):
                    response = Response(serializer.data, status=status.HTTP_406_NOT_ACCEPTABLE)
                else:
                    response = Response(serializer.data, status = status.HTTP_400_BAD_REQUEST)
        elif request.method == 'GET':
            policy = Timeoffpolicies.objects.all()
            serializer = TimeOffPoliciesSerializer(policy, many=True)
            response = Response(serializer.data, status= status.HTTP_200_OK)
        elif request.method == 'DELETE':
            try:
                policy = Timeoffpolicies.objects.get(pk=request['id'])
                policy.delete()
                response = Response(data = None, status=status.HTTP_200_OK)
            except Timeoffpolicies.DoesNotExist:
                response = Response(data=None, status= status.HTTP_204_NO_CONTENT)
        else:
            response = Response(data=None, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    # else:
    #     response = Response(data=None, status = status.HTTP_403_FORBIDDEN)

@api_view(['GET', 'POST', 'PUT', 'DELETE'])
def getTimeOffRequests(request: HttpRequest, format = None):
    # signature = request.headers.get('X-Clockify-Signature') # or wherever the signing secret is held 
    # payload = request.body
    # secret = b'' # input signing secret here 
    # auth = hmac.compare_digest(secret,payload,hashlib.sha256).hexdigest()
    # if hmac.compare_digest(auth, signature):   
        if request.method == 'POST':
            try:
                serializer = TimeOffRequestsSerializer(data = request.data)
                if serializer.is_valid():
                    # # print(serializer.data)
                    serializer.save()
                    response = Response(serializer.data, status = status.HTTP_201_CREATED)
                response = Response(serializer.data, status = status.HTTP_400_BAD_REQUEST)
            except utils.IntegrityError as e:
                if 'PRIMARY KEY constraint' in str(e):
                    response = Response(serializer.data, status=status.HTTP_304_NOT_MODIFIED)
                elif('FOREIGN KEY') in str(e):
                    response = Response(serializer.data, status=status.HTTP_406_NOT_ACCEPTABLE)
                else:
                    response = Response(serializer.data, status = status.HTTP_400_BAD_REQUEST)
        elif request.method == 'PUT':
            try:
                timeOff = Timeoffrequests.objects.get(pk=request.data['id'])
                serializer = TimeOffRequestsSerializer(instance=timeOff, data=request.data)
                if serializer.is_valid():
                    serializer.save()
                    return(Response(serializer.data, status=status.HTTP_202_ACCEPTED))
                else: 
                    return(Response(serializer.data, status= status.HTTP_400_BAD_REQUEST))
            except Timeoffrequests.DoesNotExist:
                response = Response(serializer.data, status=status.HTTP_203_NON_AUTHORITATIVE_INFORMATION)
            except utils.IntegrityError as e:
                if('FOREIGN KEY') in str(e):
                    response = Response(serializer.data, status=status.HTTP_406_NOT_ACCEPTABLE)
                else:
                    response = Response(serializer.data, status = status.HTTP_400_BAD_REQUEST)
        elif request.method == 'GET':
            timeOff = Timeoffrequests.objects.all()
            serializer = TimeOffRequestsSerializer(timeOff, many=True)
            response = Response(serializer.data, status= status.HTTP_200_OK)
        elif request.method == 'DELETE':
            try:
                timeOff = Timeoffrequests.objects.get(pk=request['id'])
                timeOff.delete()
                response = Response(data = None, status=status.HTTP_200_OK)
            except Timeoffrequests.DoesNotExist:
                response = Response(data=None, status= status.HTTP_204_NO_CONTENT)
        else:
            response = Response(data=None, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    # else:
    #     response = Response(data=None, status = status.HTTP_403_FORBIDDEN)

@api_view(['GET', 'POST', 'PUT', 'DELETE'])
def getCalendars(request: HttpRequest, format = None):
    # signature = request.headers.get('X-Clockify-Signature') # or wherever the signing secret is held 
    # payload = request.body
    # secret = b'' # input signing secret here 
    # auth = hmac.compare_digest(secret,payload,hashlib.sha256).hexdigest()
    # if hmac.compare_digest(auth, signature):   
        if request.method == 'POST':
            try:
                serializer = CalendarSerializer(data = request.data)
                if serializer.is_valid():
                    # # print(serializer.data)
                    serializer.save()
                    response = Response(serializer.data, status = status.HTTP_201_CREATED)
                response = Response(serializer.data, status = status.HTTP_400_BAD_REQUEST)
            except utils.IntegrityError as e:
                if 'PRIMARY KEY constraint' in str(e):
                    response = Response(serializer.data, status=status.HTTP_304_NOT_MODIFIED)
                elif('FOREIGN KEY') in str(e):
                    response = Response(serializer.data, status=status.HTTP_406_NOT_ACCEPTABLE)
                else:
                    response = Response(serializer.data, status = status.HTTP_400_BAD_REQUEST)
        elif request.method == 'PUT':
            try:
                day = Calendar.objects.get(pk=request.data['id'])
                serializer = CalendarSerializer(instance=day, data=request.data)
                if serializer.is_valid():
                    serializer.save()
                    return(Response(serializer.data, status=status.HTTP_202_ACCEPTED))
                else: 
                    return(Response(serializer.data, status= status.HTTP_400_BAD_REQUEST))
            except Calendar.DoesNotExist:
                response = Response(serializer.data, status=status.HTTP_203_NON_AUTHORITATIVE_INFORMATION)
            except utils.IntegrityError as e:
                if('FOREIGN KEY') in str(e):
                    response = Response(serializer.data, status=status.HTTP_406_NOT_ACCEPTABLE)
                else:
                    response = Response(serializer.data, status = status.HTTP_400_BAD_REQUEST)
        elif request.method == 'GET':
            day = Calendar.objects.all()
            serializer = CalendarSerializer(day, many=True)
            response = Response(serializer.data, status= status.HTTP_200_OK)
        elif request.method == 'DELETE':
            try:
                day = Calendar.objects.get(pk=request['id'])
                day.delete()
                response = Response(data = None, status=status.HTTP_200_OK)
            except Calendar.DoesNotExist:
                response = Response(data=None, status= status.HTTP_204_NO_CONTENT)
        else:
            response = Response(data=None, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    # else:
    #     response = Response(data=None, status = status.HTTP_403_FORBIDDEN)

@api_view(['GET', 'POST', 'PUT', 'DELETE'])
def getUserGroups(request: HttpRequest, format = None):
    # signature = request.headers.get('X-Clockify-Signature') # or wherever the signing secret is held 
    # payload = request.body
    # secret = b'' # input signing secret here 
    # auth = hmac.compare_digest(secret,payload,hashlib.sha256).hexdigest()
    # if hmac.compare_digest(auth, signature):   
        if request.method == 'POST':
            try:
                serializer = UserGroupsSerializer(data = request.data)
                if serializer.is_valid():
                    # # print(serializer.data)
                    serializer.save()
                    response = Response(serializer.data, status = status.HTTP_201_CREATED)
                response = Response(serializer.data, status = status.HTTP_400_BAD_REQUEST)
            except utils.IntegrityError as e:
                if 'PRIMARY KEY constraint' in str(e):
                    response = Response(serializer.data, status=status.HTTP_304_NOT_MODIFIED)
                elif('FOREIGN KEY') in str(e):
                    response = Response(serializer.data, status=status.HTTP_406_NOT_ACCEPTABLE)
                else:
                    response = Response(serializer.data, status = status.HTTP_400_BAD_REQUEST)
        elif request.method == 'PUT':
            try:
                group = Usergroups.objects.get(pk=request.data['id'])
                serializer = UserGroupsSerializer(instance=group, data=request.data)
                if serializer.is_valid():
                    serializer.save()
                    return(Response(serializer.data, status=status.HTTP_202_ACCEPTED))
                else: 
                    return(Response(serializer.data, status= status.HTTP_400_BAD_REQUEST))
            except Usergroups.DoesNotExist:
                response = Response(serializer.data, status=status.HTTP_203_NON_AUTHORITATIVE_INFORMATION)
            except utils.IntegrityError as e:
                if('FOREIGN KEY') in str(e):
                    response = Response(serializer.data, status=status.HTTP_406_NOT_ACCEPTABLE)
                else:
                    response = Response(serializer.data, status = status.HTTP_400_BAD_REQUEST)
        elif request.method == 'GET':
            group = Usergroups.objects.all()
            serializer = UserGroupsSerializer(group, many=True)
            response = Response(serializer.data, status= status.HTTP_200_OK)
        elif request.method == 'DELETE':
            try:
                group = Usergroups.objects.get(pk=request['id'])
                group.delete()
                response = Response(data = None, status=status.HTTP_200_OK)
            except Usergroups.DoesNotExist:
                response = Response(data=None, status= status.HTTP_204_NO_CONTENT)
        else:
            response = Response(data=None, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    # else:
    #     response = Response(data=None, status = status.HTTP_403_FORBIDDEN)

@api_view(['GET', 'POST', 'PUT', 'DELETE'])
def getGroupMembership(request: HttpRequest, format = None):
    # signature = request.headers.get('X-Clockify-Signature') # or wherever the signing secret is held 
    # payload = request.body
    # secret = b'' # input signing secret here 
    # auth = hmac.compare_digest(secret,payload,hashlib.sha256).hexdigest()
    # if hmac.compare_digest(auth, signature):   
        if request.method == 'POST':
            try:
                serializer = GroupMembershipSerializer(data = request.data)
                if serializer.is_valid():
                    # # print(serializer.data)
                    serializer.save()
                    response = Response(serializer.data, status = status.HTTP_201_CREATED)
                response = Response(serializer.data, status = status.HTTP_400_BAD_REQUEST)
            except utils.IntegrityError as e:
                if 'PRIMARY KEY constraint' in str(e):
                    response = Response(serializer.data, status=status.HTTP_304_NOT_MODIFIED)
                elif('FOREIGN KEY') in str(e):
                    response = Response(serializer.data, status=status.HTTP_406_NOT_ACCEPTABLE)
                else:
                    response = Response(serializer.data, status = status.HTTP_400_BAD_REQUEST)
        elif request.method == 'PUT':
            try:
                member = Groupmembership.objects.get(pk=request.data['id'])
                serializer = GroupMembershipSerializer(instance=member, data=request.data)
                if serializer.is_valid():
                    serializer.save()
                    return(Response(serializer.data, status=status.HTTP_202_ACCEPTED))
                else: 
                    return(Response(serializer.data, status= status.HTTP_400_BAD_REQUEST))
            except Groupmembership.DoesNotExist:
                response = Response(serializer.data, status=status.HTTP_203_NON_AUTHORITATIVE_INFORMATION)
            except utils.IntegrityError as e:
                if('FOREIGN KEY') in str(e):
                    response = Response(serializer.data, status=status.HTTP_406_NOT_ACCEPTABLE)
                else:
                    response = Response(serializer.data, status = status.HTTP_400_BAD_REQUEST)
        elif request.method == 'GET':
            member = Groupmembership.objects.all()
            serializer = GroupMembershipSerializer(member, many=True)
            response = Response(serializer.data, status= status.HTTP_200_OK)
        elif request.method == 'DELETE':
            try:
                member = Groupmembership.objects.get(pk=request['id'])
                member.delete()
                response = Response(data = None, status=status.HTTP_200_OK)
            except Groupmembership.DoesNotExist:
                response = Response(data=None, status= status.HTTP_204_NO_CONTENT)
        else:
            response = Response(data=None, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    # else:
    #     response = Response(data=None, status = status.HTTP_403_FORBIDDEN)

def getHolidays(request: HttpRequest, format = None):
    holidays = Holidays.objects.all()
    serializer = HolidaysSerializer(holidays, many=True)
    response = Response(serializer.data)
'''