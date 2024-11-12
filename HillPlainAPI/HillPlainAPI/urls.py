"""
URL configuration for HillPlainAPI project.

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
from LemApplication.views import *
from ReportGeneration.views import *


urlpatterns = [
    path('admin/', admin.site.urls),
    # path('sql', views.printSql),

    # path('quickBackup', views.quickBackup),
    # path('quickBackup/<str:event>', views.quickBackup),

# ReportGenerator App
    path('', ViewServerLog),
    path('task', ViewTaskLog),
    path('billing', BillableReport),
    path('billing/<str:month>/<str:year>/', BillableReport),
    path('billing/<str:month>/<str:year>/<str:pCode>', BillableReport),
    path('billingDateSpecific/<str:start>/<str:end>/<str:pCode>', BillableReportCustom),

    path('billingSummary', BillableNonBillable),
    path('billingSummary/<str:start_date>/<str:end_date>/', BillableNonBillable),
    path('payroll', WeeklyPayrollReport),
    path('payroll/<str:start_date>/<str:end_date>/', WeeklyPayrollReport),
    path('timeStatus', TimeStatusEvent),
    path('timeStatus/<str:start_date>/<str:end_date>/', TimeStatusEvent),
    
    path('lemsheet/<str:projectCode>/<str:lemId>/', GenerateLemView),
    path('lemsheet/<str:projectId>/<int:startMonth>/<int:startDay>/<int:startYear>/<int:endMonth>/<int:endDay>/<int:endYear>/', LemTimesheetsView),

    # path('timeSheets', views.timesheets),
    
    # path('HpClockifyApi/bankedHours', views.bankedHrs),
    # path('HpClockifyApi/updateSalaryVacation', views.accuralVacationSalary),
    
    # path('HpClockifyApi/newTimeSheets', views.newTimeSheets),
    # path('HpClockifyApi/updateTimeSheets', views.updateTimesheets),
    # path('HpClockifyApi/getClients', views.getClients),
    # path('HpClockifyApi/getUsers', views.getEmployeeUsers),
    # path('HpClockifyApi/getTimeOffPolicies', views.getTimeOffPolicies),
    # path('HpClockifyApi/getTimeOffRequests', views.getTimeOffRequests),
    # path('HpClockifyApi/removeTimeOffRequests', views.removeTimeOffRequests),
    # path('HpClockifyApi/getProjects', views.getProjects),
    # path('HpClockifyApi/newEntry', views.newEntry),
    # path('HpClockifyApi/newExpense', views.newExpense),
    # path('HpClockifyApi/deleteExpense', views.deleteExpense),
    # path('HpClockifyApi/deleteEntry', views.deleteEntry),
    # path('HpClockifyApi/requestFiles', views.requestFilesForExpense),

# LemApplication
    path('HpClockifyApi/lemSheet', lemSheet),
    path('HpClockifyApi/lemEntry', LemWorkerEntry),
    path('HpClockifyApi/equipmentEntry', equipmentEntries),
    path('HpClockifyApi/recordName', insertRoleOrEquipment),
    path('HpClockifyApi/rateSheet', rateSheets, name = 'ratesheets'),
    
    # path('HpClockifyApi/task/lemEntry', tasks.lemEntrytTask),
    
    # path('HpClockifyApi/task/retryExpense', tasks.retryExpenses),
    # path('HpClockifyApi/task/Entry', tasks.approvedEntries),
    # path('HpClockifyApi/task/Expense', tasks.approvedExpenses),

]
