from rest_framework import serializers
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
from  . import ClockifyPullV2

class WorkspaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workspace
        fields = '__all__'

class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = '__all__'

class EmployeeUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employeeuser
        fields = '__all__'

class TimeSheetSerializer(serializers.Serializer):
    id = serializers.CharField()
    owner = serializers.DictField()
    workspaceId = serializers.CharField()
    dateRange = serializers.DictField()
    status = serializers.DictField()
    def get_workspace(self, obj):
        if isinstance(obj, dict):
            return obj.get('workspaceId')
        if isinstance(obj, Timesheet):
            return obj.workspace
        else:
            raise serializers.ValidationError("Invalid data: Missing workspaceId")
    def get_emp(self, obj):
        if isinstance(obj, dict):
            owner_data = obj.get('owner', {})
            return owner_data.get('userId')
        if isinstance(obj, Timesheet):
            return obj.emp
        else:
            raise serializers.ValidationError(f"Invalid data: Missing userId {obj}")
    def get_start_time(self, obj):
        if isinstance(obj, dict):
            return ClockifyPullV2.timeZoneConvert(obj.get('dateRange').get('start'))
        if isinstance(obj, Timesheet):
            return obj.start_time
        else:
            raise serializers.ValidationError(f"Invalid data: Missing dateRange.start {obj}")
    def get_end_time(self, obj):
        if isinstance(obj, dict):
            return ClockifyPullV2.timeZoneConvert(obj.get('dateRange').get('end'))
        if isinstance(obj, Timesheet):
            return obj.end_time
        else:
            raise serializers.ValidationError("Invalid data: Missing")
    def get_status(self, obj):
        if isinstance(obj, dict):
            return obj.get('status').get('state')
        if isinstance(obj, Timesheet):
            return obj.status
        else:
            raise serializers.ValidationError("Invalid data: Missing status")
    def create(self, validated_data):
        timesheet = Timesheet.objects.create(
           id = validated_data['id'],
           workspace = self.get_workspace(validated_data),
           emp = self.get_emp(validated_data),
           start_time = self.get_start_time(validated_data),
           end_time =self.get_end_time(validated_data),
           status = self.get_status(validated_data)
        )
        return timesheet
    def update(self, instance, validated_data):
        instance.id = instance.id
        # print("\n", validated_data, '\n', vars(instance) )
        instance.workspace = self.get_workspace(validated_data) or instance.workspace
        instance.emp = self.get_emp(validated_data) or instance.emp
        instance.start_time = self.get_start_time(validated_data) or instance.start_time
        instance.end_time = self.get_end_time(validated_data) or instance.end_time
        instance.status = self.get_status(validated_data) or instance.status
        instance.save()
        return instance

    
class ProjectSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    code = serializers.SerializerMethodField()
    def get_title(self, obj):
        if isinstance(obj, dict):
            return obj.get('name', '')[10:]
        elif isinstance(obj, Project):
            return obj.name[10:]
        else:
            return ''
    def get_code(self, obj):
        if isinstance(obj, dict):
            return obj.get('name', '')[:7]
        elif isinstance(obj, Project):
            return obj.name[:7]
        else:
            return ''
    class Meta:
        model = Project
        fields = ['id', 'name', 'title', 'code', 'clientId', 'workspaceId']
    def create(self, validated_data):
        # Extract the title from validated data
        validated_data['title'] = self.get_title(validated_data)
        validated_data['code'] = self.get_code(validated_data)
        project = Project.objects.create(**validated_data)
        return project
    def update(self, instance, validated_data):
        # Update the instance with the validated data
        instance.name = validated_data.get('name', instance.name)
        instance.title = self.get_title(instance)
        instance.code = self.get_code(instance)
        instance.clientId = validated_data.get('clientId',instance.clientId)
        instance.workspaceId = validated_data.get('workspaceId',instance.workspaceId)
        instance.save()
        return instance

class EntrySerializer(serializers.Serializer): # missing update
    id = serializers.CharField()
    description = serializers.CharField(allow_blank = True)
    approvalRequestId = serializers.CharField(allow_null = True)
    billable = serializers.BooleanField()
    project = serializers.DictField()
    hourlyRate = serializers.DictField(allow_null=True)
    timeInterval = serializers.DictField()
    workspace = serializers.SerializerMethodField()
    tags = serializers.ListField()
    def to_representation(self, instance):
        if isinstance(instance, list):
            return [self.serialize_entry(obj) for obj in instance]
        else:
            return self.serialize_entry(instance)
    def serialize_entry(self, obj):
        data = {
            'id': obj.get('id') if isinstance(obj, dict) else obj.id,
            'time_sheet': self.get_time_sheet(obj),
            'duration': self.get_duration(obj),
            'description': self.get_description(obj),
            'billable': self.get_billable(obj),
            'project': self.get_project(obj),
            'rate': self.get_rate(obj),
            'start_time': self.get_start_time(obj),
            'end_time': self.get_end_time(obj),
            'workspace': self.get_workspace(obj)
        }
        return data

    def get_time_sheet(self, obj):
        return self.context.get('approvalRequestId') if isinstance(obj, dict) else obj.time_sheet
    def get_duration(self, obj):
        return ClockifyPullV2.timeDuration(obj.get('timeInterval').get('duration')) if isinstance(obj, dict) else obj.duration
    def get_description(self, obj):
        return obj.get('description') if isinstance(obj, dict) else obj.description
    def get_billable(self, obj):
        return obj.get('billable') if isinstance(obj, dict) else obj.billable
    def get_project(self, obj):
        return obj.get('project').get('id') if isinstance(obj, dict) else obj.project
    def get_rate(self, obj):
        if isinstance(obj, dict):
            return obj.get('hourlyRate').get('amount') if obj.get('hourlyRate') else 0
        if isinstance(obj, Entry):
            return obj.rate
    def get_start_time(self, obj):
        start = ClockifyPullV2.timeZoneConvert(obj.get('timeInterval').get('start')) if isinstance(obj, dict) else obj.start_time
        return start
    def get_end_time(self, obj):
        return ClockifyPullV2.timeZoneConvert(obj.get('timeInterval').get('end')) if isinstance(obj, dict) else obj.end_time
    def get_workspace(self, obj):
        return obj.workspace if isinstance(obj, Entry) else self.context.get('workspaceId')

    def create(self, validated_data):
        data = self.serialize_entry(validated_data)
        return Entry.objects.create(**data)
    
    def update(self, instance: Entry, validated_data):
        instance.id = instance.id
        instance.time_sheet = self.get_time_sheet(validated_data) or instance.time_sheet
        instance.duration = self.get_duration(validated_data) or instance.duration
        instance.description = self.get_description(validated_data) or instance.description
        instance.billable = self.get_billable(validated_data) or instance.billable
        instance.project = self.get_project(validated_data) or instance.project
        instance.rate = self.get_rate(validated_data) or instance.rate
        instance.start_time = self.get_start_time(validated_data) or instance.start_time
        instance.end_time = self.get_end_time(validated_data) or instance.end_time
        instance.workspace = self.get_workspace(validated_data) or instance.workspace
        instance.save()
        return instance

# class EntryListSerializer(serializers.ListSerializer):
#     child = EntrySerializer()
#     def update(self, queryset, validated_data):
#         instances_map = {instance.id: instance for instance in queryset}
#         updated_instances = []

#         for item in validated_data:
#             instance = instances_map.get(item['id'], None)
#             if instance:
#                 serializer = self.child(instance, data=item)
#                 if serializer.is_valid():
#                     serializer.save()
#                     updated_instances.append(serializer.instance)

#         return updated_instances

    
class TagsForSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    workspaceId = serializers.CharField()
    timeid = serializers.SerializerMethodField(method_name='get_timeid')
    entryid = serializers.SerializerMethodField(method_name='get_entryid')

    def get_timeid(self, obj):
        if isinstance(obj, dict):
            return self.context.get('timeid')
        if isinstance(obj, Tagsfor):
            return obj.timeid
    def get_entryid(self, obj):
        if isinstance(obj, dict):
            return self.context.get('entryid')
        if isinstance(obj, Tagsfor):
            return obj.timeid
    
    def to_representation(self, instance):
        if isinstance(instance, list):
            return [self.serialize_entry(obj) for obj in instance]
        else:
            return self.serialize_entry(instance)
    def serialize_entry(self, obj):
        print( obj)
        modelData = {
            'id': obj.get('id'),
            'entryid': self.get_entryid(obj),
            'timeid': self.get_timeid(obj),
            'workspace': obj.get('workspaceId'),
            'name': obj.get('name'),
        }
        return modelData
    
    def create(self, validated_data):
        data = self.to_representation(validated_data)
        tags = Tagsfor.objects.create(**data)
        return tags
    def update(self, instance, validated_data):
        instance.id = instance.id
        instance.name = validated_data.get('name') 
        instance.workspace = validated_data.get('workspaceId')
        instance.entrid = self.get_entryid(validated_data)
        instance.timeid = self.get_timeid(validated_data)
        instance.save()
        return instance
    

class TimeOffPoliciesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Timeoffpolicies
        fields = '__all__'

class TimeOffRequestsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Timeoffrequests
        fields = '__all__'

class CalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Calendar
        fields = '__all__'

class HolidaysSerializer(serializers.ModelSerializer):
    class Meta:
        model = Holidays
        fields = '__all__'

class UserGroupsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usergroups
        fields = '__all__'

class GroupMembershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = Groupmembership
        fields = '__all__'
