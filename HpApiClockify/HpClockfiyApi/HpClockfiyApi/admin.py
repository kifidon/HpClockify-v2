from django.contrib import admin 
from .models import (
    Workspace,
    Employeeuser,
    Timesheet,
    Project,
    Entry,
    Tagsfor,
)

admin.site.register(Employeeuser)
admin.site.register(Workspace)
admin.site.register(Timesheet)
admin.site.register(Entry)
admin.site.register(Project)
admin.site.register(Tagsfor)