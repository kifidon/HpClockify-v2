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
    Category
)
from .clockify_util.hpUtil import timeZoneConvert, timeDuration, get_current_time
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
    workspaceId = serializers.PrimaryKeyRelatedField(queryset=Workspace.objects.all())
    tags = serializers.ListField()

    def create(self, validated_data):
        logger = setup_background_logger('DEBUG')
        logger.info('Create Entry Called')
        if validated_data.get('hourlyRate') is not None:
            Rate = validated_data.get('hourlyRate').get('amount')
        else: Rate = -1
        try: 
            timesheet = Timesheet.objects.get(id=self.context.get('approvalRequestId')) 
        except Timesheet.DoesNotExist:
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
            workspaceId = validated_data.get('workspaceId') or self.context.get('workspaceId'),
        )
        return entry
    
    def update(self, instance: Entry, validated_data):
        logger = setup_background_logger('DEBUG')
        logger.info('Update Entry Called')
        try:
            # instance.id = instance.id
            instance.timesheetId = Timesheet.objects.get(id=validated_data['timesheetId']) or instance.timesheetId
            instance.duration = timeDuration(validated_data.get('timeInterval').get('duration')) or instance.duration
            instance.description = validated_data.get('description') or instance.description
            instance.billable = validated_data.get('billable') or instance.billable
            instance.project = Project.objects.get(id=validated_data.get('project').get('id')) or instance.project
            if validated_data.get('hourlyRate') is not None:     
                instance.rate = validated_data.get('hourlyRate').get('amount') 
            else: instance.hourlyRate =  -1
            instance.start = timeZoneConvert(validated_data.get('timeInterval').get('start')) or instance.start
            instance.end = timeZoneConvert(validated_data.get('timeInterval').get('end')) or instance.end
            instance.workspaceId = Workspace.objects.get(id= self.context.get('workspaceId')) or instance.workspaceId
            instance.save(force_update=True)
            return instance
        except Exception as e:
            logger.warning(f'UnknownError: {dumps(str(e), indent = 4)}')
            return instance

class TagsForSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    workspaceId = serializers.CharField()
    timeid = serializers.SerializerMethodField(method_name='get_timeid')
    entryid = serializers.SerializerMethodField(method_name='get_entryid')

    def create(self,validated_data:dict):
        logger = setup_background_logger('DEBUG')
        logger.info('Create Tag Called')
        entry =  Entry.objects.get(
                id=self.context.get('entryid'),
                time_sheet= self.context.get('timeid') , 
                workspace=validated_data.get('workspaceId')
            )
        print(entry)
        tag = Tagsfor.objects.create(
            id = validated_data.get('id'),
            entryid = Entry.objects.get(
                id=self.context.get('entryid'),
                time_sheet= self.context.get('timeid') , 
                workspace=validated_data.get('workspaceId')
            ),
            timeid = Timesheet.objects.get(id=self.context.get('timeid')),
            workspace = Workspace.objects.get(id= validated_data.get('workspaceId')),
            name = validated_data.get('name')
        )
        return tag
    
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
        