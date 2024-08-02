from rest_framework import serializers
from . Loggers import setup_background_logger
from .models import *
from rest_framework.exceptions import ValidationError
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
    Truck = serializers.SerializerMethodField() 

    def get_status(self, obj):
        status = obj['status']
        return status 
    
    def get_hasTruck(self, obj):
        logger = setup_background_logger() 
        field = dict()
        for custom in obj['userCustomFields']:
            field[custom['name']] = custom['value']
        try:
            if field['Truck']:
                return 1
            else:
                return 0
        except Exception as e: 
            logger.debug(type(e))
            
            return 0
    
    def get_role(self, obj):
        field = dict()
        for custom in obj['userCustomFields']:
            field[custom['name']] = custom['value']
        try:
            return field['Role']
        except Exception: 
            return 'No Role Specified'
    
    def get_start_date(self, obj): 
        field = dict()
        for custom in obj['userCustomFields']:
            field[custom['name']] = custom['value']
        try:
            return field['Start Date']
        except Exception: 
            return date.today().strftime('%Y-%m-%d')
    
    def create(self, validated_data):
        logger = setup_background_logger() 
        try:
            logger.debug(self.initial_data)
            validated_data['status'] = self.get_status(self.initial_data)
            validated_data['Truck'] = self.get_hasTruck(self.initial_data)
            validated_data['role'] = self.get_role(self.initial_data)
            validated_data['start_date'] = self.get_start_date(self.initial_data) 
            logger.info(dumps(validated_data, indent = 4))
            return super().create(validated_data=validated_data)
        except Exception as e: 
            logger.error(f'Problem inserting User Data {e.__traceback__.tb_lineno}: ({str(e)})')

    def update(self, instance, validated_data):
        logger = setup_background_logger() 
        logger.debug(self.initial_data)
        try:
            validated_data['status'] = self.get_status(self.initial_data)
            validated_data['role'] = self.get_role(self.initial_data)
            validated_data['start_date'] = self.get_start_date(self.initial_data)
            validated_data['Truck'] = self.get_hasTruck(self.initial_data)
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
        logger.debug(validated_data)
        if validated_data['billable'] == True:
            if validated_data.get('hourlyRate') is None:
                logger.critical('No Rate on billable Entry')
                raise ValidationError()
            Rate = validated_data.get('hourlyRate').get('amount')
        try: 
            timesheet = Timesheet.objects.get(id=validated_data['timesheetId']) 
        except Exception as e:
            timesheet = None 
        logger.debug(validated_data['billable'])
        entry = Entry.objects.create(
            id= validated_data['id'],
            timesheetId = timesheet,
            duration = timeDuration(validated_data.get('timeInterval').get('duration')),
            description = validated_data.get('description'),
            billable = validated_data['billable'] ,
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
        logger.debug(validated_data)
        try:
            logger.debug(f"Billlable -({validated_data['billable']})")
            # instance.id = instance.id
            try:
                instance.timesheetId = Timesheet.objects.get(id=validated_data['timesheetId']) 
            except Exception as e:
                instance.timesheetId
                logger.debug(type(e))
            instance.duration = timeDuration(validated_data.get('timeInterval').get('duration')) or instance.duration
            instance.description = validated_data.get('description') or instance.description
            instance.billable = validated_data['billable'] if validated_data['billable'] != None else instance.billable
            instance.project = Project.objects.get(id=validated_data.get('project').get('id')) or instance.project
            if validated_data.get('hourlyRate') is not None:     
                instance.hourlyRate = validated_data.get('hourlyRate').get('amount') 
            else: instance.hourlyRate =  -1
            instance.start = timeZoneConvert(validated_data.get('timeInterval').get('start')) or instance.start
            instance.end = timeZoneConvert(validated_data.get('timeInterval').get('end')) or instance.end
            # instance.workspaceId = Workspace.objects.get(id= validated_data.get('workspaceId')) or instance.workspaceId
            instance.save(force_update=True)
            return instance
        except Exception as e:
            logger.warning(f'UnknownError: {e.__traceback__.tb_lineno} {dumps(str(e), indent = 4)}')
            raise e

class TagsForSerializer(serializers.ModelSerializer):
    '''
    Input is of the form: 
    {
        "entryid": "adasdfadf ada"
        "archived": true,
        "id": "64c777ddd3fcab07cfbb210c",
        "name": "Sprint1",
        "workspaceId": "64a687e29ae1f428e7ebe303"
    }
    '''
    # entryid = serializers.SerializerMethodField(method_name='get_entryid')
    
    class Meta:
        model= Tagsfor
        fields = "__all__"

    
    
    # def create(self,validated_data:dict):
    #     try: 
    #         logger = setup_background_logger('DEBUG')
    #         logger.info('Create Tag Called')
    #         entryInstnace = Entry.objects.get(
    #                             id=self.get_entryid(),
    #                             workspaceId=validated_data.get('workspaceId')
    #                         )
    #         tag = Tagsfor.objects.create(
    #             id = validated_data.get('id'),
    #             entryid = entryInstnace,
    #             workspaceId = Workspace.objects.get(id= validated_data.get('workspaceId')),
    #             name = validated_data.get('name')
    #         )
    #         return tag
    #     except Exception as e:
    #         logger.error(f'Error Caught ({e.__traceback__.tb_lineno}): {str(e)}')
    #         raise e 
    
    def update(self, instance, validated_data):
        logger = setup_background_logger('DEBUG')
        logger.info('Update Tag Called')
        try:
            instance.name = validated_data.get('name', instance.name)
            
            # Ensuring that primary key fields are not changed
            # instance.id = instance.id
            # instance.workspace = instance.workspace
            # instance.entryid = instance.entryid

            # Save the instance
            logger.warning(f"\tUpdate on Tags For Entry is a Forbidden Opperation. Returning...")
            return instance
        except Exception as e:
            logger.warning(f'UnknownError: {dumps(str(e), indent=4)}')
            raise e

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
    date = serializers.DateField(input_formats=['%m/%d/%Y'])
    
    class Meta:
        model = Expense
        fields = "__all__"
        
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

class FileExpenseSerializer(serializers.ModelSerializer):

    class Meta: 
        model = FilesForExpense
        fields = "__all__"

#########################################################################################################################################################################################################
class LemSheetSerializer(serializers.ModelSerializer):
    lem_sheet_date = serializers.DateField(input_formats=['%m/%d/%Y', '%Y-%m-%d'])
    class Meta:
        model = LemSheet
        fields = '__all__'

class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = '__all__'

class EquipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Equipment
        fields = '__all__'

class LemWorkerSerializer(serializers.ModelSerializer):
    class Meta:
        model = LemWorker
        fields = '__all__'

class LemEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = LemEntry
        fields = '__all__'

class EquipEntrySerializer(serializers.ModelSerializer):
    '''
    {
        "lemId": "461fb94fbedf7499259ba46606260df60c6a00323e62c",
        "workspaceId": "65c249bfedeea53ae19d7dad",
        "equipId": "919394",
        "isUnitRate": 1,
        "qty": "9"
    }
    '''
    class Meta:
        model = EquipEntry
        fields = '__all__'

class WorkerRateSheetSerializer(serializers.ModelSerializer):
    '''
    {
        "clientId": "65c25a26c642257db282938b",
        "roleId": "36ba9e042df56922a8917f834bc7e951ea2d7f33e81d7",
        "workspaceId": "65c249bfedeea53ae19d7dad",
        "workRate": 32,
        "travelRate": 42,
        "calcRate": 12,
        "isRole": true
    }
    '''
    class Meta:
        model = WorkerRateSheet
        fields = '__all__'

class EqpRateSheetSerializer(serializers.ModelSerializer):
    '''
    {
        "clientId": "65c25a26c642257db282938b",
        "equipId": "919394",
        "workspaceId": "65c249bfedeea53ae19d7dad",
        "unitRate": 322,
        "dayRate": 4122,
        "isRole": false
    }
    '''
    class Meta:
        model = EqpRateSheet
        fields = '__all__'

class ClientRepSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientRep
        fields = '__all__'