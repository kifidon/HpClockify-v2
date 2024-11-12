from django.contrib import admin
from .models import BackGroundTaskResult


@admin.register(BackGroundTaskResult)
class BackGroundTaskResultAdmin(admin.ModelAdmin):
    list_display = ('status_code', 'message', 'time', 'caller')
    search_fields = ('caller', 'message')
    list_filter = ('status_code', 'time')
    ordering = ('-time',)
    date_hierarchy = 'time'

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ['status_code', 'message', 'data', 'time', 'caller']
        return []
