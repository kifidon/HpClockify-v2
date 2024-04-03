from django.http import JsonResponse, HttpRequest
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
@api_view(['GET', 'POST'])
def getWorkspaces(request: HttpRequest, format = None):
    workspaces = Workspace.objects.all()
    serializer = WorkspaceSerializer(workspaces, many=True)
    return JsonResponse(serializer.data, safe=False)

@api_view(['GET', 'PUT', 'POST', 'DELETE'])
def getClients(request: HttpRequest, format = None):
    if request.method == 'GET':
        clients = Client.objects.all()
        serializer = ClientSerializer(clients, many=True)
        return JsonResponse(serializer.data, safe=False)
    elif request.method == 'PUT':
        pass
    elif request.method == 'POST':
        pass
    elif request.method == 'DELETE':
        pass

@api_view(['GET', 'POST'])
def getEmployeeUsers(request: HttpRequest, format = None):
    if request.method == 'GET':
        employeeUsers = Employeeuser.objects.all()
        serializer = EmployeeUserSerializer(employeeUsers, many=True)
        return JsonResponse(serializer.data, safe=False)
    if request.method == 'POST':
        serializer = EmployeeUserSerializer(data = request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status = status.HTTP_201_CREATED)

@api_view(['GET', 'PUT', 'DELETE'])        
def EmployeeUser_detail(request: HttpRequest,  id: str, format = None):
    try:
        user = Employeeuser.objects.get(pk=id)
    except Employeeuser.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    if request.method == 'GET':
        serializer = EmployeeUserSerializer(user)
        return Response(serializer.data, status = status.HTTP_200_OK)
    elif request.method == 'PUT':
        serializer = EmployeeUserSerializer(user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return(Response(serializer.data))
        else:
            return Response( serializer.errors, status = status.HTTP_400_BAD_REQUEST)
    elif request.method == 'Delete':
        user.delete()
        return Response(status- status.HTTP_204_NO_CONTENT)

def getTimeSheets(request: HttpRequest, format = None):
    timeSheets = Timesheet.objects.all()
    serializer = TimeSheetSerializer(timeSheets, many=True)
    return JsonResponse(serializer.data, safe=False)

@api_view(['GET', 'POST', 'PUT'])
def getProjects(request: HttpRequest, format = None):
    if request.method == 'POST':
        try:
            serializer = ProjectSerializer(data = request.data)
            if serializer.is_valid():
                # print(serializer.data)
                    serializer.save()
                    return Response(serializer.data, status = status.HTTP_201_CREATED)
        except pyodbc.IntegrityError as e:
            if 'PRIMARY KEY constraint' in str(e):
                return Response(serializer.data, status=status.HTTP_304_NOT_MODIFIED)
            elif('FOREIGN KEY') in str(e):
                return Response(serializer.data, status=status.HTTP_406_NOT_ACCEPTABLE)
            else:
                return Response(serializer.data, status = status.HTTP_400_BAD_REQUEST)
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
            return Response(status=status.HTTP_203_NON_AUTHORITATIVE_INFORMATION)
        except pyodbc.IntegrityError as e:
            if('FOREIGN KEY') in str(e):
                return Response(serializer.data, status=status.HTTP_406_NOT_ACCEPTABLE)
            else:
                return Response(serializer.data, status = status.HTTP_400_BAD_REQUEST)
    elif request.method == 'GET':
        projects = Project.objects.all()
        serializer = ProjectSerializer(projects, many=True)
        return JsonResponse(serializer.data, status= status.HTTP_200_OK, safe=False)

def getEntries(request: HttpRequest, format = None):
    entries = Entry.objects.all()
    serializer = EntrySerializer(entries, many=True)
    return JsonResponse(serializer.data, safe=False)

def getTagsFor(request: HttpRequest, format = None):
    tagsFor = Tagsfor.objects.all()
    serializer = TagsForSerializer(tagsFor, many=True)
    return JsonResponse(serializer.data, safe=False)

def getTimeOffPolicies(request: HttpRequest, format = None):
    timeOffPolicies = Timeoffpolicies.objects.all()
    serializer = TimeOffPoliciesSerializer(timeOffPolicies, many=True)
    return JsonResponse(serializer.data, safe=False)

def getTimeOffRequests(request: HttpRequest, format = None):
    timeOffRequests = Timeoffrequests.objects.all()
    serializer = TimeOffRequestsSerializer(timeOffRequests, many=True)
    return JsonResponse(serializer.data, safe=False)

def getCalendars(request: HttpRequest, format = None):
    calendars = Calendar.objects.all()
    serializer = CalendarSerializer(calendars, many=True)
    return JsonResponse(serializer.data, safe=False)

def getHolidays(request: HttpRequest, format = None):
    holidays = Holidays.objects.all()
    serializer = HolidaysSerializer(holidays, many=True)
    return JsonResponse(serializer.data, safe=False)

def getUserGroups(request: HttpRequest, format = None):
    userGroups = Usergroups.objects.all()
    serializer = UserGroupsSerializer(userGroups, many=True)
    return JsonResponse(serializer.data, safe=False)

def getGroupMembership(request: HttpRequest, format = None):
    groupMembership = Groupmembership.objects.all()
    serializer = GroupMembershipSerializer(groupMembership, many=True)
    return JsonResponse(serializer.data, safe=False)