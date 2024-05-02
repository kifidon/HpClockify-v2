from django.contrib import admin 
from .models import (
    Workspace,
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

admin.site.register(Employeeuser)
admin.site.register(Usergroups)
admin.site.register(Workspace)
admin.site.register(Timeoffpolicies)
admin.site.register(Timeoffrequests)
admin.site.register(Timesheet)
admin.site.register(Entry)
admin.site.register(Project)
admin.site.register(Tagsfor)
admin.site.register(Calendar)
admin.site.register(Holidays)
admin.site.register(Groupmembership)