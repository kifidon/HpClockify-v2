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
from Clockify.views import * 
from Clockify import tasks

urlpatterns = [
    # path('admin/', admin.site.urls), impliment later 
    # path('sql', views.printSql),

# Clockified Scheduled tasks
    path('quickBackup', QuickBackup),
    path('quickBackup/<str:event>', QuickBackup),

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
    
    path('HpClockifyApi/bankedHours', BankedHrs),
    path('HpClockifyApi/updateSalaryVacation', UpdateSalaryVacation),

#Hill Plain internal Clockify API
    path('HpClockifyApi/TimeSheets', TimesheetsView),
    path('HpClockifyApi/Clients', ClientsView),
    path('HpClockifyApi/Users', EmployeeUsersView),
    path('HpClockifyApi/TimeOff', TimeOffRequestsView),
    path('HpClockifyApi/Policies', TimeOffPoliciesView),
    path('HpClockifyApi/Projects', ProjectsView, name='projects'),
    path('HpClockifyApi/Entry', EntryView),
    # path('HpClockifyApi/newExpense', views.newExpense),
    # path('HpClockifyApi/deleteExpense', views.deleteExpense),
    # path('HpClockifyApi/requestFiles', views.requestFilesForExpense),

    path('HpClockifyApi/task/lemEntry', tasks.lemEntrytTask),
    path('HpClockifyApi/task/Entry', tasks.approvedEntries),

# LemApplication
    path('HpClockifyApi/lemSheet', lemSheet),
    path('HpClockifyApi/lemEntry', LemWorkerEntry),
    path('HpClockifyApi/equipmentEntry', equipmentEntries),
    path('HpClockifyApi/recordName', insertRoleOrEquipment),
    path('HpClockifyApi/rateSheet', rateSheets, name = 'ratesheets'),
    
    
    # path('HpClockifyApi/task/retryExpense', tasks.retryExpenses),
    # path('HpClockifyApi/task/Expense', tasks.approvedExpenses),

]
