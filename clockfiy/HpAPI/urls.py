"""HpAPI URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from HpAPI import views
from rest_framework.urlpatterns import format_suffix_patterns

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.view_log),
    path('quickBackup', views.quickBackup),
    path('HpClockifyAPi/bankedHours', views.bankedHrs),
    path('billableReport', views.download_text_file),
    path('billableReport/<str:start_date>/<str:end_date>/', views.download_text_file),
    # path('HpClockifyAPi/getWorkspaces', views.getWorkspaces),
    path('HpClockifyAPi/getClients', views.getClients),
    path('HpClockifyAPi/getUsers', views.getEmployeeUsers),
    path('HpClockifyAPi/getTimeSheets', views.getTimeSheets),
    path('HpClockifyAPi/updateTimeSheets', views.updateTimesheet),
    path('HpClockifyAPi/getProjects', views.getProjects),
    path('timeSheets', views.timesheets),
    # path('HpClockifyAPi/getEntries', views.getEntries),
    # path('HpClockifyAPi/getTagsFor', views.getTagsFor),
    path('HpClockifyAPi/getTimeOffPolicies', views.getTimeOffPolicies),
    path('HpClockifyAPi/getTimeOffRequests', views.getTimeOffRequests),
    # path('HpClockifyAPi/getCalendars', views.getCalendars),
    # path('HpClockifyAPi/getHolidays', views.getHolidays),
    # path('HpClockifyAPi/getUserGroups', views.getUserGroups),
    # path('HpClockifyAPi/getGroupMembership', views.getGroupMembership),
]

urlpatterns = format_suffix_patterns(urlpatterns)