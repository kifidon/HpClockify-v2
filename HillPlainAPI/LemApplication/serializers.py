from rest_framework import serializers
from .models import *

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