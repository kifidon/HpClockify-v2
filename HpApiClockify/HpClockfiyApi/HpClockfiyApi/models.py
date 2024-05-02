# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
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
    id = models.CharField(primary_key=True, max_length=50)  # The composite primary key (id, workspace_id) found, that is not supported. The first column is selected.
    email = models.CharField(max_length=50, blank=True, null=True)
    address = models.CharField(max_length=100, blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    workspace = models.ForeignKey('Workspace', models.DO_NOTHING, to_field='id', db_column= 'workspace_id')

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
    start_date = models.DateField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'EmployeeUser'

class Timesheet(models.Model):
    id = models.CharField(max_length=50, primary_key=True)
    emp = models.ForeignKey('Employeeuser', models.DO_NOTHING, to_field='id', db_column='emp_id')  # The composite primary key (emp_id, id, workspace_id) found, that is not supported. The first column is selected.
    start_time = models.DateField(blank=True, null=True)
    end_time = models.DateField(blank=True, null=True)
    workspace = models.ForeignKey('Workspace', models.DO_NOTHING, db_column='workspace_id')
    status = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'TimeSheet'
        unique_together = (('emp', 'id', 'workspace'), ('id', 'workspace'),)

class Project(models.Model):
    id = models.CharField(primary_key=True, max_length=50)  # The composite primary key (id, workspace_id, workspace_id) found, that is not supported. The first column is selected.
    name = models.TextField(blank=True, null=True)
    title = models.TextField(blank=True, null=True)
    code = models.CharField(max_length=50, blank=True, null=True)
    client = models.ForeignKey(Client, models.DO_NOTHING, to_field='id', db_column='client_id')
    workspace = models.ForeignKey('Workspace', models.DO_NOTHING, to_field='id',db_column='workspace_id')

    class Meta:
        managed = False
        db_table = 'Project'
        unique_together = (('id', 'workspace', 'workspace'),)

class Entry(models.Model):
    id = models.CharField(primary_key=True, max_length=50)  # The composite primary key (id, time_sheet_id, workspace_id, workspace_id) found, that is not supported. The first column is selected.
    time_sheet = models.ForeignKey('Timesheet', models.DO_NOTHING, to_field='id', db_column='time_sheet_id')
    duration = models.FloatField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    billable = models.BooleanField(blank=True, null=True)
    project = models.ForeignKey('Project', models.DO_NOTHING, to_field='id', blank=True, null=True, db_column='project_id')
    # type = models.CharField(max_length=20, blank=True, null=True)
    rate = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    start_time = models.DateTimeField(blank=True, null=True)
    end_time = models.DateTimeField(blank=True, null=True)
    workspace = models.ForeignKey('Workspace', models.DO_NOTHING, db_column='workspace_id', to_field='id')

    class Meta:
        managed = False
        db_table = 'Entry'
        unique_together = (('id', 'time_sheet', 'workspace'))

class Tagsfor(models.Model):
    id = models.CharField(primary_key=True, max_length=50)  # The composite primary key (id, entryID, timeID, workspace_id) found, that is not supported. The first column is selected.
    entryid = models.ForeignKey('Entry', models.DO_NOTHING, db_column='entryID', to_field='id')  # Field name made lowercase.
    timeid = models.ForeignKey('TimeSheet', models.DO_NOTHING, db_column='timeID', to_field='id')  # Field name made lowercase.
    workspace = models.ForeignKey('Workspace', models.DO_NOTHING, db_column='workspace_id')
    name = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'TagsFor'
        unique_together = (('id', 'entryid', 'timeid', 'workspace'),)


##################################################################################################################################################################################################
class AuthGroup(models.Model):
    name = models.CharField(max_length=150)

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
    username = models.CharField(max_length=30)
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
