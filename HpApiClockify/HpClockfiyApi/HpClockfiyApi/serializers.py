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
class TimesheetSerializer(serializers.Serializer):
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

class EntrySerializer(serializers.Serializer): # missing update
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
    class Meta: 
        model = Category
        fields = ['id','hasUnitPrice', 'archived', 'name', 'priceInCents', 'unit', 'workspaceId']

class ExpenseSerializer(serializers.ModelSerializer):
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

