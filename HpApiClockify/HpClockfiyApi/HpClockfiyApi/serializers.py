from rest_framework import serializers
from . Loggers import setup_background_logger
from .models import(
    Employeeuser,
    Workspace,
    Timesheet,
    Entry,
    Project,
    Tagsfor,
    Expense, 
    Category,
    TimeOffRequests
)
from .clockify_util.hpUtil import count_working_daysV2, timeZoneConvert, timeDuration, get_current_time
from json import dumps
from datetime import date
class EmployeeUserSerializer(serializers.ModelSerializer):
    '''
    Serialized to the EmployeeUser Model fields. 
    Input Data is of the form: 
        {
            "id": "65dcdd57ea15ab53ab7b14db",
            "email": "kendal.cruz@hillplain.com",
            "name": "Kendal Cruz",
            "profilePicture": "https://img.clockify.me/no-user-image.png",
            "settings": {
                "weekStart": "SUNDAY",
                "timeZone": "America/Edmonton",
                "timeFormat": "HOUR12",
                "dateFormat": "MM/DD/YYYY",
                "sendNewsletter": false,
                "weeklyUpdates": false,
                "longRunning": false,
                "scheduledReports": true,
                "approval": true,
                "pto": true,
                "alerts": true,
                "reminders": true,
                "onboarding": true,
                "timeTrackingManual": false,
                "summaryReportSettings": {
                    "group": "Project",
                    "subgroup": "Time Entry"
                },
                "isCompactViewOn": false,
                "dashboardSelection": "ME",
                "dashboardViewType": "PROJECT",
                "dashboardPinToTop": false,
                "projectListCollapse": 50,
                "collapseAllProjectLists": false,
                "groupSimilarEntriesDisabled": false,
                "myStartOfDay": "08:30",
                "darkTheme": true,
                "projectPickerSpecialFilter": false,
                "lang": "EN",
                "multiFactorEnabled": false,
                "scheduling": true,
                "showOnlyWorkingDays": false,
                "theme": "DARK"
            },
            "userCustomFields": [
                {
                    "customFieldId": "664d0d0a6a8fa06c786a886e",
                    "value": "HSEA",
                    "name": "Role",
                    "type": "DROPDOWN_SINGLE"
                },
                {
                    "customFieldId": "664d0d56a17be2283ae908ec",
                    "value": "2024-01-22",
                    "name": "Start Date",
                    "type": "TXT"
                }
            ]
        } 
    '''
    status = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    start_date = serializers.SerializerMethodField()  # validate this later 
    
    def get_status(self, obj):
        status = obj['status']
        return status 

    def get_role(self, obj):
        field = dict()
        for custom in obj['userCustomFields']:
            field[custom['name']] = custom['value']
        try:
            return field['Role']
        except Exception: 
            return 'No Role Specified'
    
    def get_start_date(sekf, obj): 
        field = dict()
        for custom in obj['userCustomFields']:
            field[custom['name']] = custom['value']
        try:
            return field['Start Date']
        except Exception: 
            return date.today()
    
    def create(self, validated_data):
        logger = setup_background_logger() 
        try:
            validated_data['status'] = self.get_status(self.initial_data)
            validated_data['role'] = self.get_role(self.initial_data)
            validated_data['start_date'] = self.get_start_date(self.initial_data) 
            logger.info(dumps(validated_data, indent = 4))
            return super().create(validated_data=validated_data)
        except Exception as e: 
            logger.error(f'Problem inserting User Data {e.__traceback__.tb_lineno}: ({str(e)})')

    def update(self, instance, validated_data):
        logger = setup_background_logger() 
        try:
            validated_data['status'] = self.get_status(self.context)
            validated_data['role'] = self.get_role(self.initial_data)
            validated_data['start_date'] = self.get_start_date(self.initial_data)
            logger.debug(dumps(validated_data, indent = 4))
            updated = super().update(instance= instance, validated_data=validated_data)
            updated.save(force_update= True )
            return updated 
        except Exception as e: 
            logger.error(f'Problem Updating User Data {e.__traceback__.tb_lineno}: ({str(e)})')
            raise e
    class Meta:
        model = Employeeuser
        fields = '__all__'

class TimesheetSerializer(serializers.Serializer):
    '''
    Input is of the form: 
    {
        "id": "664d12ce831d3f5360a7c43c",
        "workspaceId": "65c249bfedeea53ae19d7dad",
        "dateRange": {
            "start": "2024-05-12T06:00:00Z",
            "end": "2024-05-19T05:59:59Z"
        },
        "owner": {
            "userId": "65dcdd57ea15ab53ab7b14d0",
            "userName": "Mohamad Potts",
            "timeZone": "America/Denver",
            "startOfWeek": "SUNDAY"
        },
        "status": {
            "state": "APPROVED",
            "updatedBy": "65dcdd57ea15ab53ab7b14d0",
            "updatedByUserName": "Mohamad Potts",
            "updatedAt": "2024-05-21T21:31:58Z",
            "note": ""
        },
        "creator": {
            "userId": "65dcdd57ea15ab53ab7b14d0",
            "userName": "Mohamad Potts",
            "userEmail": "mohamad.potts@hillplain.com"
        }
    }
    '''
    id = serializers.CharField()
    owner = serializers.DictField()
    workspaceId = serializers.CharField()
    dateRange = serializers.DictField()
    status = serializers.DictField()
   
    def create(self, validated_data):
       
        timesheet = Timesheet.objects.create(
           id = validated_data['id'],
           workspace = Workspace.objects.get(id=validated_data['workspaceId']),
           emp = Employeeuser.objects.get(id=validated_data.get('owner').get('userId')),
           start_time = timeZoneConvert(validated_data.get('dateRange').get('start')),
           end_time = timeZoneConvert(validated_data.get('dateRange').get('end')),
           status = validated_data.get('status').get('state')
        )
        return timesheet

    def update(self, instance: Timesheet, validated_data):
        try:
            instance.id = instance.id
            # print("\n", validated_data, '\n', vars(instance) )
            instance.workspace = Workspace.objects.get(id=validated_data['workspaceId']) or instance.workspace
            instance.emp = Employeeuser.objects.get(id = validated_data.get('owner').get('userId')) or instance.emp
            instance.start_time = timeZoneConvert(validated_data.get('dateRange').get('start')) or instance.start_time
            instance.end_time = timeZoneConvert(validated_data.get('dateRange').get('end'))or instance.end_time
            instance.status = validated_data.get('status').get('state') or instance.status
            instance.save(force_update=True)
        except Exception as e:
            print(e.__traceback__.tb_lineno)
            raise e 
        return instance

class EntrySerializer(serializers.Serializer): 
    '''
    Input is of the form: 
    {
        "approvalRequestId": "5e4117fe8c625f38930d57b7",
        "billable": true,
        "costRate": {},
        "customFieldValues": [],
        "description": "This is a sample time entry description.",
        "hourlyRate": {},
        "id": "5b715448b0798751107918ab",
        "isLocked": true,
        "project": {},
        "tags": [],
        "task": {},
        "timeInterval": {},
        "type": "REGULAR"
    }
    '''
    id = serializers.CharField()
    description = serializers.CharField(allow_blank = True)
    timesheetId = serializers.CharField(allow_null = True, allow_blank=True, required=False)
    billable = serializers.BooleanField()
    project = serializers.DictField()
    hourlyRate = serializers.DictField(allow_null=True)
    timeInterval = serializers.DictField()
    workspaceId = serializers.CharField()
    tags = serializers.ListField()

    def create(self, validated_data):
        logger = setup_background_logger('DEBUG')
        logger.info('Create Entry Called')
        if validated_data.get('hourlyRate') is not None:
            Rate = validated_data.get('hourlyRate').get('amount')
        else: Rate = -1
        try: 
            timesheet = Timesheet.objects.get(id=validated_data['timesheetId']) 
        except Exception as e:
            timesheet = None 
        entry = Entry.objects.create(
            id= validated_data['id'],
            timesheetId = timesheet,
            duration = timeDuration(validated_data.get('timeInterval').get('duration')),
            description = validated_data.get('description'),
            billable = validated_data.get('billable') ,
            project = Project.objects.get(id=validated_data.get('project').get('id')),
            hourlyRate = Rate,
            start = timeZoneConvert(validated_data.get('timeInterval').get('start')),
            end = timeZoneConvert(validated_data.get('timeInterval').get('end')),
            workspaceId = Workspace.objects.get(id=validated_data.get('workspaceId')) ,
        )
        return entry
    
    def update(self, instance: Entry, validated_data):
        logger = setup_background_logger('DEBUG')
        logger.info('Update Entry Called')
        try:
            # instance.id = instance.id
            try:
                instance.timesheetId = Timesheet.objects.get(id=validated_data['timesheetId']) 
            except Exception as e:
                instance.timesheetId
                logger.debug(type(e))
            instance.duration = timeDuration(validated_data.get('timeInterval').get('duration')) or instance.duration
            instance.description = validated_data.get('description') or instance.description
            instance.billable = validated_data.get('billable') or instance.billable
            instance.project = Project.objects.get(id=validated_data.get('project').get('id')) or instance.project
            if validated_data.get('hourlyRate') is not None:     
                instance.rate = validated_data.get('hourlyRate').get('amount') 
            else: instance.hourlyRate =  -1
            instance.start = timeZoneConvert(validated_data.get('timeInterval').get('start')) or instance.start
            instance.end = timeZoneConvert(validated_data.get('timeInterval').get('end')) or instance.end
            # instance.workspaceId = Workspace.objects.get(id= validated_data.get('workspaceId')) or instance.workspaceId
            instance.save(force_update=True)
            return instance
        except Exception as e:
            logger.warning(f'UnknownError: {e.__traceback__.tb_lineno} {dumps(str(e), indent = 4)}')
            return instance

class TagsForSerializer(serializers.Serializer):
    '''
    Input is of the form: 
    {
        "archived": true,
        "id": "64c777ddd3fcab07cfbb210c",
        "name": "Sprint1",
        "workspaceId": "64a687e29ae1f428e7ebe303"
    }
    '''
    id = serializers.CharField()
    name = serializers.CharField()
    workspaceId = serializers.CharField()
    timeid = serializers.SerializerMethodField(method_name='get_timeid')
    entryid = serializers.SerializerMethodField(method_name='get_entryid')

    def create(self,validated_data:dict):
        try: 
            logger = setup_background_logger('DEBUG')
            logger.info('Create Tag Called')
            
            tag = Tagsfor.objects.create(
                id = validated_data.get('id'),
                entryid = Entry.objects.get(
                    id=self.context.get('entryid'),
                    timesheetId= self.context.get('timeid') , 
                    workspaceId=validated_data.get('workspaceId')
                ),
                timeid = Timesheet.objects.get(id=self.context.get('timeid')),
                workspace = Workspace.objects.get(id= validated_data.get('workspaceId')),
                name = validated_data.get('name')
            )
            return tag
        except Exception as e:
            logger.error(f'Error Caught ({e.__traceback__.tb_lineno}): {str(e)}')
            raise e 
    
    def update( self , instance: Tagsfor, validated_data):
        logger = setup_background_logger('DEBUG')
        logger.info('Update Tag Called')
        try:
            # instance.id = instance.id
            instance.name = validated_data.get('name') or instance.name
            # instance.workspace =  Workspace.objects.get(id= validated_data.get('workspaceId')) or instance.workspace
            # instance.entryid = Entry.objects.get(id=self.context.get('entryid'), workspace=validated_data.get('workspaceId')) or instance.entryid
            instance.timeid = Timesheet.objects.get(id=self.context.get('timeid')) or instance.timeid
            instance.save(force_update=True)
            return instance
        except Exception as e: 
            logger.warning(f'UnknownError: {dumps(str(e), indent = 4)}')
            return instance
    
class CategorySerializer(serializers.ModelSerializer): 
    '''
    Input is of the form: 
        {
            "archived": true,
            "hasUnitPrice": true,
            "id": "89a687e29ae1f428e7ebe303",
            "name": "Procurement",
            "priceInCents": 1000,
            "unit": "piece",
            "workspaceId": "64a687e29ae1f428e7ebe303"
        }
    '''
    class Meta: 
        model = Category
        fields = ['id','hasUnitPrice', 'archived', 'name', 'priceInCents', 'unit', 'workspaceId']

class ExpenseSerializer(serializers.ModelSerializer):
    '''
    Input is of the form: 
        {
            "id": "66463e0a58c2983f17f453ae",
            "workspaceId": "65c249bfedeea53ae19d7dad",
            "userId": "661d41f8680b5d3887e576e8",
            "date": "2024-05-16T00:00:00Z",
            "projectId": "65c5185e824ced2beacffa9a",
            "categoryId": "65c2522effbbb676c5e010b4",
            "notes": "Paid Elder for smudge ceremony",
            "quantity": 1,
            "billable": true,
            "fileId": "",
            "total": 10000
        }
    '''
    date = serializers.DateField(input_formats=['%Y-%m-%dT%H:%M:%SZ'])
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['workspaceId'] = str(instance['workspaceId'])
        data['userId'] = str(instance['userId']) 
        data['projectId'] = str(instance['projectId']) 
        return data
    class Meta:
        model = Expense
        fields = ['id', 'workspaceId','userId', 'date', 'categoryId', 'projectId',  'notes', 'quantity', 'billable', 'fileId', 'timesheetId', 'total']
        
class TimeOffSerializer(serializers.ModelSerializer): 
    '''
    Input is of the form: 
        {
            "workspaceId": "65c249bfedeea53ae19d7dad",
            "policyId": "65fc91ca17e548286f7bc026",
            "userId": "65bd6a6077682a20767a6c0b",
            "timeZone": "America/Edmonton",
            "timeOffPeriod": {
                "period": {
                    "start": "2024-05-14T14:00:00Z",
                    "end": "2024-05-14T22:00:00Z"
                },
                "halfDay": false,
                "halfDayPeriod": "NOT_DEFINED"
            },
            "note": null,
            "status": {
                "statusType": "PENDING",
                "changedByUserId": null,
                "changedByUserName": "Timmy Ifidon",
                "changedAt": null,
                "note": null
            },
            "balanceDiff": 8,
            "createdAt": "2024-05-21T18:15:52.889302519Z",
            "requesterUserId": "65bd6a6077682a20767a6c0b",
            "excludeDays": [],
            "negativeBalanceUsed": 0,
            "balanceValueAtRequest": 15,
            "id": "664ce4d8c8a2333cfdc245cc"
        }
    '''
    status = serializers.SerializerMethodField()
    start = serializers.SerializerMethodField()
    end = serializers.SerializerMethodField()
    
    def validate_status(self, value):
        logger = setup_background_logger()  # Assuming setup_background_logger is defined elsewhere
        try: 
            if value.get('statusType'): 
                return value
            else:
                raise serializers.ValidationError("Missing 'statusType' in status")
        except KeyError as e:
            logger.info(f'Key Error: {e}')
            raise serializers.ValidationError(f"Key Error: {e}")
        except Exception as e: 
            logger.error(f'Error during status validation: {e}')
            raise serializers.ValidationError(f"Error during status validation: {e}")
            
    def create(self, validated_data):
        logger = setup_background_logger()
        start = timeZoneConvert(self.initial_data.get('timeOffPeriod').get('period').get('start'))
        end = timeZoneConvert(self.initial_data.get('timeOffPeriod').get('period').get('end'))
        status = self.initial_data.get('statusType')
        excludeDays = self.initial_data.get('excludeDays')
        duration = count_working_daysV2(start, end, excludeDays)
        logger.debug(status)
        if start and end and status and duration:
            validated_data['start'] = start
            validated_data['end'] = end
            validated_data['status'] = status 
            validated_data['duration'] = duration
        # handle FK objects 
        validated_data['userId'] = Employeeuser.objects.get(id=validated_data['userId'].id)
        validated_data['workspaceId'] = Workspace.objects.get(pk=validated_data['workspaceId'].id)
        return super().create(validated_data=validated_data)

    def update(self, instance, validated_data): 
        logger = setup_background_logger()
        start = timeZoneConvert(self.initial_data.get('timeOffPeriod').get('period').get('start'))
        end = timeZoneConvert(self.initial_data.get('timeOffPeriod').get('period').get('end'))
        status = self.initial_data.get('status').get('statusType')
        excludeDays = self.initial_data.get('excludeDays')
        duration = count_working_daysV2(start, end, excludeDays)
        logger.debug('status')
        if start and end and status and duration:
            validated_data['start'] = start
            validated_data['end'] = end
            validated_data['status'] = status 
            validated_data['duration'] = duration
        # handle FK objects 
        validated_data['userId'] = Employeeuser.objects.get(id=validated_data['userId'].id)
        validated_data['workspaceId'] = Workspace.objects.get(id=validated_data['workspaceId'].id)
        updated_instance =  super().update(instance=instance, validated_data=validated_data)
        # Then, save the instance with force_update=True
        updated_instance.save(force_update=True)
        return updated_instance
        
    
    class Meta: 
        model = TimeOffRequests
        fields = '__all__'

