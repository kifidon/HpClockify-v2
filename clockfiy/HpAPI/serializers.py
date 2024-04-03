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

class TimeSheetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Timesheet
        fields = '__all__'


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

class EntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Entry
        fields = '__all__'

class TagsForSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tagsfor
        fields = '__all__'

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
