from django.contrib import admin
from .models import (
    LemSheet, Role, Equipment, LemWorker, LemEntry, EquipEntry,
    WorkerRateSheet, EqpRateSheet, ClientRep
)

@admin.register(LemSheet)
class LemSheetAdmin(admin.ModelAdmin):
    list_display = ('id', 'lem_sheet_date', 'lemNumber', 'projectId', 'clientId', 'workspaceId', 'archived')
    search_fields = ('id', 'lemNumber', 'description')
    list_filter = ('archived', 'workspaceId')

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'clientId', 'workspaceId')
    search_fields = ('name',)
    list_filter = ('clientId', 'workspaceId')

@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'clientId', 'workspaceId')
    search_fields = ('name',)
    list_filter = ('clientId', 'workspaceId')

@admin.register(LemWorker)
class LemWorkerAdmin(admin.ModelAdmin):
    list_display = ('_id', 'empId', 'roleId')
    search_fields = ('empId',)
    list_filter = ('roleId',)

@admin.register(LemEntry)
class LemEntryAdmin(admin.ModelAdmin):
    list_display = ('_id', 'lemId', 'workerId', 'work', 'travel', 'calc', 'meals', 'hotel')
    search_fields = ('lemId', 'workerId')
    list_filter = ('lemId',)

@admin.register(EquipEntry)
class EquipEntryAdmin(admin.ModelAdmin):
    list_display = ('_id', 'lemId', 'equipId', 'isUnitRate', 'qty')
    search_fields = ('lemId', 'equipId')
    list_filter = ('isUnitRate', 'lemId')

@admin.register(WorkerRateSheet)
class WorkerRateSheetAdmin(admin.ModelAdmin):
    list_display = ('_id', 'clientId', 'roleId', 'workRate', 'travelRate', 'calcRate', 'mealRate', 'hotelRate', 'workspaceId', 'projectId')
    search_fields = ('clientId', 'roleId')
    list_filter = ('workspaceId', 'projectId')

@admin.register(EqpRateSheet)
class EqpRateSheetAdmin(admin.ModelAdmin):
    list_display = ('_id', 'clientId', 'equipId', 'unitRate', 'dayRate', 'workspaceId', 'projectId')
    search_fields = ('clientId', 'equipId')
    list_filter = ('workspaceId', 'projectId')

@admin.register(ClientRep)
class ClientRepAdmin(admin.ModelAdmin):
    list_display = ('_id', 'empId', 'clientId', 'workspaceId')
    search_fields = ('empId', 'clientId')
    list_filter = ('workspaceId',)

# Optional: Customize the admin site headers
admin.site.site_header = "Project Management Admin"
admin.site.site_title = "Project Management Portal"
admin.site.index_title = "Welcome to the Project Management Admin Portal"
