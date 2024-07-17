"""
URL configuration for HpClockfiyApi project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
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
from . import views
from . import tasks

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.viewServerLog),
    path('task', views.viewTaskLog),

    path('quickBackup', views.quickBackup),
    path('billableReport', views.monthlyBillableReport),
    path('billableReport/<str:month>/<str:year>/', views.monthlyBillableReport),
    path('billableReportEqp', views.monthlyBillableReportEquipment),
    path('billableReportEqp/<str:month>/<str:year>/', views.monthlyBillableReportEquipment),
    path('payroll', views.weeklyPayrollReport),
    path('payroll/<str:start_date>/<str:end_date>/', views.weeklyPayrollReport),
    path('getTime', views.dailyTimeEntry),
    
    path('timeSheets', views.timesheets),
    
    path('HpClockifyApi/bankedHours', views.bankedHrs),
    path('HpClockifyApi/newTimeSheets', views.newTimeSheets),
    path('HpClockifyApi/updateTimeSheets', views.updateTimesheets),
    path('HpClockifyApi/getClients', views.getClients),
    path('HpClockifyApi/getUsers', views.getEmployeeUsers),
    path('HpClockifyApi/getTimeOffPolicies', views.getTimeOffPolicies),
    path('HpClockifyApi/getTimeOffRequests', views.getTimeOffRequests),
    path('HpClockifyApi/removeTimeOffRequests', views.removeTimeOffRequests),
    path('HpClockifyApi/getProjects', views.getProjects),
    path('HpClockifyApi/newEntry', views.newEntry),
    path('HpClockifyApi/newExpense', views.newExpense),
    path('HpClockifyApi/deleteExpense', views.deleteExpense),
    path('HpClockifyApi/deleteEntry', views.deleteEntry),
    path('HpClockifyApi/requestFiles', views.requestFilesForExpense),
    
    path('HpClockifyApi/lemSheet', views.lemSheet),
    path('HpClockifyApi/lemEntry', views.LemWorkerEntry),
    path('HpClockifyApi/equipmentEntry', views.equipmentEntries),
    
    path('HpClockifyApi/task/lemEntry', tasks.lemEntrytTask),
    
    path('HpClockifyApi/task/retryExpense', tasks.retryExpenses),
    path('HpClockifyApi/task/Entry', tasks.approvedEntries),
    path('HpClockifyApi/task/Expense', tasks.approvedExpenses),

]

