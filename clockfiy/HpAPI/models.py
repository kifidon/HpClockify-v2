# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey has `on_delete` set to the desired behavior.
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class Workspace(models.Model):
    id = models.CharField(primary_key=True, max_length=50)
    name = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Workspace'

class Calendar(models.Model):
    date = models.DateField(primary_key=True)
    dayofweek = models.IntegerField(db_column='dayOfWeek', blank=True, null=True)  # Field name made lowercase.
    month = models.IntegerField(blank=True, null=True)
    year = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Calendar'


class Client(models.Model):
    id = models.CharField(primary_key=True, max_length=50)
    email = models.CharField(max_length=50, blank=True, null=True)
    address = models.CharField(max_length=100, blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    workspace = models.ForeignKey(Workspace, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'Client'
        unique_together = (('id', 'workspace'),)

class Employeeuser(models.Model):
    id = models.CharField(primary_key=True, max_length=50)
    email = models.CharField(max_length=255, blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=50, blank=True, null=True)
    baserate = models.DecimalField(db_column='baseRate', max_digits=10, decimal_places=2, blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'EmployeeUser'

class Timesheet(models.Model):
    id = models.CharField(primary_key=True, max_length=50)
    emp = models.ForeignKey(Employeeuser, models.DO_NOTHING)
    start_time = models.DateField(blank=True, null=True)
    end_time = models.DateField(blank=True, null=True)
    approved_time = models.FloatField(blank=True, null=True)
    billable_time = models.FloatField(blank=True, null=True)
    billable_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    cost_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    expense_total = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    workspace = models.ForeignKey(Workspace, models.DO_NOTHING)
    status = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'TimeSheet'
        unique_together = (('id', 'workspace'),)


class Project(models.Model):
    id = models.CharField(primary_key=True, max_length=50, db_column = 'id')
    name = models.CharField(max_length = 100, null=False, db_column = 'name')
    title = models.CharField(max_length=50, null=False, db_column = 'title')
    code = models.CharField(max_length=50, null = False,  db_column = 'code')
    clientId = models.CharField( max_length=50, db_column = 'client_id')
    workspaceId = models.CharField(max_length=50, db_column = 'workspace_id')

    class Meta:
        managed = False
        db_table = 'Project'
        unique_together = (('id', 'workspaceId'),)

class Entry(models.Model):
    id = models.CharField(primary_key=True, max_length=50)
    time_sheet = models.ForeignKey(Timesheet, models.DO_NOTHING)
    duration = models.FloatField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    billable = models.BooleanField(blank=True, null=True)
    project = models.ForeignKey(Project, models.DO_NOTHING, blank=True, null=True)
    type = models.CharField(max_length=20, blank=True, null=True)
    rate = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    start_time = models.DateTimeField(blank=True, null=True)
    end_time = models.DateTimeField(blank=True, null=True)
    workspace = models.ForeignKey(Workspace, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Entry'
        unique_together = (('id', 'time_sheet'),)

class Usergroups(models.Model):
    id = models.CharField(primary_key=True, max_length=50)
    name = models.CharField(unique=True, max_length=50, blank=True, null=True)
    workspace = models.ForeignKey(Workspace, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'UserGroups'
        unique_together = (('id', 'workspace'),)

class Groupmembership(models.Model):
    user = models.OneToOneField(Employeeuser, models.DO_NOTHING, primary_key=True)
    group = models.ForeignKey(Usergroups, models.DO_NOTHING,)
    workspace = models.ForeignKey(Workspace, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'GroupMembership'
        unique_together = (('user', 'group', 'workspace'),)


class Holidays(models.Model):
    holidayid = models.CharField(db_column='holidayID', primary_key=True, max_length=50)  # Field name made lowercase.
    date = models.ForeignKey(Calendar, models.DO_NOTHING, db_column='date', blank=True, null=True)
    name = models.CharField(max_length=50, blank=True, null=True)
    workspace = models.ForeignKey(Workspace, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'Holidays'
        unique_together = (('holidayid', 'workspace'),)



class Tagsfor(models.Model):
    id = models.CharField(primary_key=True, max_length=50)
    entryid = models.ForeignKey(Entry, models.DO_NOTHING, related_name= 'tag_entryID', db_column='entryID')  # Field name made lowercase.
    timeid = models.ForeignKey(Entry, models.DO_NOTHING, db_column='timeID')  # Field name made lowercase.
    workspace = models.ForeignKey(Workspace, models.DO_NOTHING)
    name = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'TagsFor'
        unique_together = (('id', 'entryid', 'timeid', 'workspace'),)


class Timeoffpolicies(models.Model):
    id = models.CharField(primary_key=True, max_length=50)
    policy_name = models.CharField(max_length=50, blank=True, null=True)
    accrual_amount = models.FloatField(blank=True, null=True)
    accrual_period = models.CharField(max_length=15, blank=True, null=True)
    time_unit = models.CharField(max_length=14, blank=True, null=True)
    archived = models.BooleanField(blank=True, null=True)
    wid = models.ForeignKey(Workspace, models.DO_NOTHING, db_column='wID')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'TimeOffPolicies'
        unique_together = (('id', 'wid'),)


class Timeoffrequests(models.Model):
    id = models.CharField(primary_key=True, max_length=50)
    eid = models.ForeignKey(Employeeuser, models.DO_NOTHING, db_column='eID')  # Field name made lowercase.
    pid = models.ForeignKey(Timeoffpolicies, models.DO_NOTHING, db_column='pID')  # Field name made lowercase.
    startdate = models.DateTimeField(db_column='startDate', blank=True, null=True)  # Field name made lowercase.
    end_date = models.DateTimeField(blank=True, null=True)
    duration = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    paidtimeoff = models.DecimalField(db_column='paidTimeOff', max_digits=10, decimal_places=2, blank=True, null=True)  # Field name made lowercase.
    balanceafterrequest = models.DecimalField(db_column='balanceAfterRequest', max_digits=10, decimal_places=2, blank=True, null=True)  # Field name made lowercase.
    status = models.CharField(max_length=50, blank=True, null=True)
    workspace = models.ForeignKey(Workspace, models.DO_NOTHING, related_name = 'timeOff_workspace')

    class Meta:
        managed = False
        db_table = 'TimeOffRequests'
        unique_together = (('id', 'workspace', 'workspace'),)





class AuthGroup(models.Model):
    name = models.CharField(unique=True, max_length=80)

    class Meta:
        managed = False
        db_table = 'auth_group'


class AuthGroupPermissions(models.Model):
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)
    permission = models.ForeignKey('AuthPermission', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_group_permissions'
        unique_together = (('group', 'permission'),)


class AuthPermission(models.Model):
    name = models.CharField(max_length=255)
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING)
    codename = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'auth_permission'
        unique_together = (('content_type', 'codename'),)


class AuthUser(models.Model):
    password = models.CharField(max_length=128)
    last_login = models.DateTimeField(blank=True, null=True)
    is_superuser = models.BooleanField()
    username = models.CharField(unique=True, max_length=150)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=150)
    email = models.CharField(max_length=254)
    is_staff = models.BooleanField()
    is_active = models.BooleanField()
    date_joined = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'auth_user'


class AuthUserGroups(models.Model):
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_groups'
        unique_together = (('user', 'group'),)


class AuthUserUserPermissions(models.Model):
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    permission = models.ForeignKey(AuthPermission, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_user_permissions'
        unique_together = (('user', 'permission'),)


# class ClockifyCalendar(models.Model):
#     date = models.DateField(primary_key=True)
#     day_of_week = models.IntegerField()
#     month = models.IntegerField()
#     year = models.IntegerField()

#     class Meta:
#         managed = False
#         db_table = 'clockify_calendar'


# class ClockifyClient(models.Model):
#     id = models.CharField(primary_key=True, max_length=50)
#     email = models.CharField(max_length=255)
#     address = models.CharField(max_length=100)
#     name = models.CharField(max_length=255)
#     workspace = models.ForeignKey('ClockifyWorkspace', models.DO_NOTHING)

#     class Meta:
#         managed = False
#         db_table = 'clockify_client'


# class ClockifyEmployeeuser(models.Model):
#     id = models.CharField(primary_key=True, max_length=50)
#     email = models.CharField(max_length=255)
#     name = models.CharField(max_length=255)
#     status = models.CharField(max_length=50)
#     baserate = models.DecimalField(db_column='baseRate', max_digits=10, decimal_places=2)  # Field name made lowercase.

#     class Meta:
#         managed = False
#         db_table = 'clockify_employeeuser'


# class ClockifyEntry(models.Model):
#     id = models.BigAutoField(primary_key=True)
#     entryid = models.CharField(db_column='entryId', max_length=50)  # Field name made lowercase.
#     duration = models.FloatField()
#     description = models.TextField()
#     billable = models.BooleanField()
#     type = models.CharField(max_length=20)
#     rate = models.DecimalField(max_digits=10, decimal_places=2)
#     start_time = models.DateTimeField()
#     end_time = models.DateTimeField()
#     project = models.ForeignKey('ClockifyProject', models.DO_NOTHING)
#     time_sheet = models.ForeignKey('ClockifyTimesheet', models.DO_NOTHING)
#     workspace = models.ForeignKey('ClockifyWorkspace', models.DO_NOTHING)

#     class Meta:
#         managed = False
#         db_table = 'clockify_entry'


# class ClockifyGroupmembership(models.Model):
#     id = models.BigAutoField(primary_key=True)
#     group = models.ForeignKey('ClockifyUsergroups', models.DO_NOTHING)
#     user = models.ForeignKey(ClockifyEmployeeuser, models.DO_NOTHING)
#     workspace = models.ForeignKey('ClockifyWorkspace', models.DO_NOTHING)

#     class Meta:
#         managed = False
#         db_table = 'clockify_groupmembership'


# class ClockifyHolidays(models.Model):
#     holidayid = models.CharField(db_column='holidayID', primary_key=True, max_length=50)  # Field name made lowercase.
#     date = models.DateField()
#     name = models.CharField(max_length=50)
#     workspace = models.ForeignKey('ClockifyWorkspace', models.DO_NOTHING)

#     class Meta:
#         managed = False
#         db_table = 'clockify_holidays'


# class ClockifyProject(models.Model):
#     id = models.CharField(primary_key=True, max_length=50)
#     name = models.CharField(max_length=255)
#     code = models.CharField(max_length=50)
#     client = models.ForeignKey(ClockifyClient, models.DO_NOTHING)
#     workspace = models.ForeignKey('ClockifyWorkspace', models.DO_NOTHING)

#     class Meta:
#         managed = False
#         db_table = 'clockify_project'


# class ClockifyTagsfor(models.Model):
#     id = models.CharField(primary_key=True, max_length=50)
#     timeid = models.CharField(db_column='timeID', max_length=50)  # Field name made lowercase.
#     name = models.CharField(max_length=50)
#     entry = models.ForeignKey(ClockifyEntry, models.DO_NOTHING)
#     workspace = models.ForeignKey('ClockifyWorkspace', models.DO_NOTHING)

#     class Meta:
#         managed = False
#         db_table = 'clockify_tagsfor'


# class ClockifyTimeoffpolicies(models.Model):
#     id = models.CharField(primary_key=True, max_length=50)
#     policy_name = models.CharField(max_length=50)
#     accrual_amount = models.FloatField()
#     accrual_period = models.CharField(max_length=15)
#     time_unit = models.CharField(max_length=14)
#     archived = models.BooleanField()
#     workspace = models.ForeignKey('ClockifyWorkspace', models.DO_NOTHING)

#     class Meta:
#         managed = False
#         db_table = 'clockify_timeoffpolicies'


# class ClockifyTimeoffrequests(models.Model):
#     id = models.CharField(primary_key=True, max_length=50)
#     start_date = models.DateTimeField()
#     end_date = models.DateTimeField()
#     duration = models.DecimalField(max_digits=10, decimal_places=2)
#     paid_time_off = models.DecimalField(max_digits=10, decimal_places=2)
#     balance_after_request = models.DecimalField(max_digits=10, decimal_places=2)
#     status = models.CharField(max_length=50)
#     employee = models.ForeignKey(ClockifyEmployeeuser, models.DO_NOTHING)
#     policy = models.ForeignKey(ClockifyTimeoffpolicies, models.DO_NOTHING)
#     workspace = models.ForeignKey('ClockifyWorkspace', models.DO_NOTHING)

#     class Meta:
#         managed = False
#         db_table = 'clockify_timeoffrequests'


# class ClockifyTimesheet(models.Model):
#     id = models.CharField(primary_key=True, max_length=50)
#     start_time = models.DateField()
#     end_time = models.DateField()
#     approved_time = models.FloatField()
#     billable_time = models.FloatField()
#     billable_amount = models.DecimalField(max_digits=10, decimal_places=2)
#     cost_amount = models.DecimalField(max_digits=10, decimal_places=2)
#     expense_total = models.DecimalField(max_digits=10, decimal_places=2)
#     status = models.CharField(max_length=50)
#     emp_id = models.ForeignKey(ClockifyEmployeeuser, models.DO_NOTHING)
#     workspace = models.ForeignKey('ClockifyWorkspace', models.DO_NOTHING)

#     class Meta:
#         managed = False
#         db_table = 'clockify_timesheet'


# class ClockifyUsergroups(models.Model):
#     id = models.CharField(primary_key=True, max_length=50)
#     name = models.CharField(unique=True, max_length=50)
#     workspace = models.ForeignKey('ClockifyWorkspace', models.DO_NOTHING)

#     class Meta:
#         managed = False
#         db_table = 'clockify_usergroups'


# class ClockifyWorkspace(models.Model):
#     id = models.CharField(primary_key=True, max_length=50)
#     name = models.CharField(max_length=50)

#     class Meta:
#         managed = False
#         db_table = 'clockify_workspace'


class DjangoAdminLog(models.Model):
    action_time = models.DateTimeField()
    object_id = models.TextField(blank=True, null=True)
    object_repr = models.CharField(max_length=200)
    action_flag = models.SmallIntegerField()
    change_message = models.TextField()
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING, blank=True, null=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'django_admin_log'


class DjangoContentType(models.Model):
    app_label = models.CharField(max_length=100)
    model = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'django_content_type'
        unique_together = (('app_label', 'model'),)


class DjangoMigrations(models.Model):
    app = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    applied = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_migrations'


class DjangoSession(models.Model):
    session_key = models.CharField(primary_key=True, max_length=40)
    session_data = models.TextField()
    expire_date = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_session'