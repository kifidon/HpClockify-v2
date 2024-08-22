
from django.db import models

class Workspace(models.Model):
    id = models.CharField(primary_key=True, max_length=50)
    name = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Workspace'
    
    def __str__(self):
        return self.name or ""

class Calendar(models.Model):
    date = models.DateField(primary_key=True)
    dayofweek = models.IntegerField(db_column='dayOfWeek', blank=True, null=True)  # Field name made lowercase.
    month = models.IntegerField(blank=True, null=True)
    year = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Calendar'

    def __str__(self):
        return self.date or ""
    
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

    def __str__(self):
        return self.name or ""
    
class Employeeuser(models.Model):
    id = models.CharField(primary_key=True, max_length=50)
    email = models.CharField(max_length=255, blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=50, blank=True, null=True)
    role = models.CharField(db_column='role', max_length=50, blank=True, null=True)  # Field name made lowercase.
    manager = models.CharField(db_column='manager', max_length=50, blank=True, null=True)  # Field name made lowercase.
    start_date = models.DateField(blank=True, null=True)
    Truck = models.IntegerField(blank= False, null = True, default=0, db_column='hasTruck')
    hourly = models.IntegerField(blank = True, null = True, default = 0, db_column = 'hourly')
    class Meta:
        managed = False
        db_table = 'EmployeeUser'

    def __str__(self):
        return self.name or ""
    
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

    def __str__(self):
        return self.id or ""
    
class Project(models.Model):
    id = models.CharField(primary_key=True, max_length=50)  # The composite primary key (id, workspace_id, workspace_id) found, that is not supported. The first column is selected.
    name = models.TextField(blank=True, null=True)
    title = models.TextField(blank=True, null=True)
    code = models.CharField(max_length=50, blank=True, null=True)
    clientId = models.ForeignKey(Client, models.DO_NOTHING, to_field='id', db_column='client_id')
    workspaceId = models.ForeignKey('Workspace', models.DO_NOTHING, to_field='id',db_column='workspace_id')

    class Meta:
        managed = False
        db_table = 'Project'
        unique_together = (('id', 'workspace', 'workspace'),)

    def __str__(self):
        return self.name or ""
    
class Entry(models.Model):
    id = models.CharField(primary_key=True, max_length=50)  # The composite primary key (id, time_sheet_id, workspace_id, workspace_id) found, that is not supported. The first column is selected.
    timesheetId = models.ForeignKey('Timesheet', models.DO_NOTHING, to_field='id', db_column='time_sheet_id', blank=True, null=True)
    duration = models.FloatField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    billable = models.BooleanField(blank=True, null=True)
    project = models.ForeignKey('Project', models.CASCADE, to_field='id', blank=True, null=True, db_column='project_id')
    # type = models.CharField(max_length=20, blank=True, null=True)
    hourlyRate = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, db_column='rate')
    start = models.DateTimeField(blank=True, null=True, db_column='start_time')
    end = models.DateTimeField(blank=True, null=True, db_column='end_time')
    workspaceId = models.ForeignKey('Workspace', models.DO_NOTHING, db_column='workspace_id', to_field='id')

    class Meta:
        managed = False
        db_table = 'Entry'
        unique_together = (('id',  'workspaceId'))

    def __str__(self):
        return self.id or ""
    
class Tagsfor(models.Model):
    recordId = models.CharField(max_length= 50, primary_key=True)
    id = models.CharField(max_length=50)  # The composite primary key (id, entryID, timeID, workspace_id) found, that is not supported. The first column is selected.
    entryid = models.ForeignKey(Entry, models.DO_NOTHING, db_column='entryID')  # Field name made lowercase.
    workspaceId = models.ForeignKey(Workspace, models.DO_NOTHING, db_column='workspace_id')
    name = models.CharField(max_length=50, blank=True, null=True)
    class Meta:
        managed = False
        db_table = 'TagsFor'
        unique_together = (('id', 'entryid', 'workspace'),)

    def __str__(self):
        return self.name or ""
    
class Category(models.Model):
    id = models.CharField(primary_key=True,max_length = 50 )
    name = models.CharField( max_length=50, blank=False, null = False)
    hasUnitPrice = models.BooleanField(default=False, max_length=1)
    unit = models.CharField(max_length=50, blank=True, null= True)
    workspaceId = models.ForeignKey(Workspace, models.DO_NOTHING, db_column='workspaceId', to_field='id' )
    archived = models.BooleanField(default=False, max_length=1)
    priceInCents = models.IntegerField(default = 0, null=True, blank=True )
    class Meta:
        managed = False
        db_table = 'ExpenseCategory'
        unique_together = (('id', 'workspaceId'))

    def __str__(self):
        return self.name or ""
    
class Expense(models.Model):
    id = models.CharField(primary_key=True,max_length = 64 )
    workspaceId = models.ForeignKey(Workspace, models.DO_NOTHING, db_column='workspaceId')
    userId = models.ForeignKey(Employeeuser, models.DO_NOTHING, db_column='userId')
    date = models.DateField(blank=False, null = False)
    projectId = models.ForeignKey(Project, models.DO_NOTHING , db_column='projectId')
    categoryId = models.ForeignKey(Category, models.DO_NOTHING, db_column='categoryId' )
    notes = models.TextField(blank=True, null=True)
    quantity = models.FloatField( blank=True, null=True)
    subTotal = models.FloatField( blank=True, null=True)
    taxes = models.FloatField( blank=True, null=True)
    status = models.CharField( max_length = 50, default = 'PENDING', blank= True, null=True)
    

    class Meta:
        managed = False
        db_table = 'Expense'
        unique_together= (('id', 'workspaceId'))

    def __str__(self):
        return self.id or ""

class TimeOffRequests(models.Model):
    id = models.CharField(primary_key =True, max_length =50)
    userId = models.ForeignKey(Employeeuser, models.DO_NOTHING, db_column='eID')
    policyId = models.CharField(blank=False, null = False, max_length=50, db_column= 'pID')
    start = models.DateTimeField(blank = False, null = False, db_column='startDate')
    end = models.DateTimeField(blank = False, null = False, db_column='end_date')
    duration = models.FloatField(default = 0)
    balanceDiff = models.FloatField(default = 0, db_column='paidTimeOff')
    status = models.CharField(max_length=50)
    workspaceId = models.ForeignKey(Workspace, models.DO_NOTHING, db_column='workspace_id')

    class Meta:
        managed = False
        db_table = 'TimeOffRequests'
        unique_together = (('id', 'workspaceId'))

class FilesForExpense(models.Model):
    expenseId = models.CharField(max_length=64, primary_key=True, db_column= 'expenseId')
    workspaceId = models.CharField(max_length=50, db_column='workspaceId')
    binaryData = models.TextField(db_column='binaryData')
    class Meta: 
        managed = False 
        db_table = 'FilesForExpense'
        unique_together= (('expenseId', 'workspaceId'))


class BackGroundTaskResult(models.Model):
    status_code = models.IntegerField(default=404)
    message = models.TextField(blank=True, null= True)
    data = models.TextField(blank=False, null=False )
    time = models.DateTimeField(blank=False, null=False)
    caller = models.CharField(max_length=50 )
    class Meta:
        managed = False
        db_table = 'BackGroundTaskDjango'

##################################################################################################################################################################################################

class LemSheet(models.Model):
    id = models.CharField(max_length = 50, primary_key=True) #  date, and project
    lem_sheet_date = models.DateField(blank=False, null=False)
    lemNumber = models.CharField(max_length = 10, blank = False, null = False)
    description = models.TextField(blank=True, null=True )
    notes = models.TextField(blank = True, null= True)
    projectId = models.ForeignKey(Project, on_delete=models.CASCADE, db_column= 'projectId')
    projectManagerId = models.ForeignKey(Employeeuser, models.DO_NOTHING, db_column='projectManagerId')
    clientId = models.ForeignKey(Client, on_delete=models.DO_NOTHING, db_column= 'clientId')
    workspaceId = models.ForeignKey(Workspace, models.DO_NOTHING, db_column='workspaceId')
    archived = models.BooleanField(blank=True, default=False)
    clientRep = models.CharField(blank=True, null=True, max_length=50, default= "----")
    class Meta:
        managed = False
        db_table = 'LemSheet'
        constraints = [
            models.UniqueConstraint(fields=['id', 'workspaceId'], name='unique_client_lem')
        ]

class Role(models.Model):
    id = models.CharField(max_length = 50, primary_key= True) #hashed by name
    name = models.CharField(max_length = 50, blank= False, null = False)
    clientId = models.ForeignKey(Client, on_delete=models.DO_NOTHING, db_column= 'clientId')
    workspaceId = models.ForeignKey(Workspace, models.DO_NOTHING, db_column='workspaceId')
    
    class Meta: 
        managed = False
        db_table = 'Role'

class Equipment(models.Model):
    id = models.CharField(primary_key=True, max_length=50, null=False, blank=False)
    name = models.CharField(max_length=50, null=False, blank= False)
    clientId = models.ForeignKey(Client, on_delete=models.DO_NOTHING, db_column= 'clientId')
    workspaceId = models.ForeignKey(Workspace, models.DO_NOTHING, db_column='workspaceId')    
    class Meta: 
        managed = False
        db_table = 'Equipment'
        
class LemWorker(models.Model):
    _id = models.CharField(primary_key=True, max_length=50, null=False, blank=False)
    empId = models.CharField(max_length=50, null=False, blank= False,db_column=  'name') # 
    roleId = models.ForeignKey(Role, on_delete=models.DO_NOTHING, db_column='roleId')
    class Meta: 
        managed = False
        db_table = 'LemWorker'
        constraints = [
            models.UniqueConstraint(fields=['empId', 'roleId'], name='unique_emp_role')
        ]

class LemEntry(models.Model):
    _id = models.CharField(primary_key=True, max_length=50, null=False, blank=False)# hashed by lemId and workerId
    lemId = models.ForeignKey(LemSheet, on_delete=models.CASCADE, db_column='lemId') 
    workerId = models.ForeignKey(LemWorker, on_delete=models.DO_NOTHING, db_column='workerId')
    work = models.DecimalField(max_digits=10, decimal_places=2,blank=True,null=True, default=0.00)
    travel = models.DecimalField(max_digits=10, decimal_places=2,blank=True,null=True, default=0.00)
    calc = models.DecimalField(max_digits=10, decimal_places=2,blank=True,null=True, default=0.00)
    meals = models.DecimalField(max_digits=10, decimal_places=2,blank=True,null=True, default=0.00)
    hotel = models.DecimalField(max_digits=10, decimal_places=2,blank=True,null=True, default=0.00)
    class Meta:
        managed = False
        db_table = 'LemEntry'
        constraints = [
            models.UniqueConstraint(fields=['workerId', 'lemId'], name='unique_worker_entry')
        ]

class EquipEntry(models.Model):
    _id = models.CharField(primary_key=True, max_length=50)
    lemId = models.ForeignKey(LemSheet, on_delete=models.CASCADE, db_column='lemId')
    equipId = models.ForeignKey(Equipment, on_delete=models.DO_NOTHING, db_column='equipId')
    isUnitRate = models.BooleanField()
    qty = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, default=0.00)
    class Meta:
        managed = False
        db_table = "EquipEntry"

class WorkerRateSheet(models.Model):
    _id = models.CharField(primary_key=True, max_length=50, null=False, blank=False)
    clientId = models.ForeignKey(Client, on_delete= models.CASCADE, db_column='clientId', blank=False, null=False)
    roleId = models.ForeignKey(Role, on_delete=models.DO_NOTHING, db_column='roleId', blank=False, null= False)
    workRate = models.DecimalField(max_digits=10, decimal_places=2,blank=True,null=True, default=0.00)
    travelRate =  models.DecimalField(max_digits=10, decimal_places=2,blank=True,null=True, default=0.00)
    calcRate =  models.DecimalField(max_digits=10, decimal_places=2,blank=True,null=True, default=0.00)
    mealRate =  models.DecimalField(max_digits=10, decimal_places=2,blank=True,null=True, default=0.00)
    hotelRate =  models.DecimalField(max_digits=10, decimal_places=2,blank=True,null=True, default=0.00)
    workspaceId = models.ForeignKey(Workspace, models.DO_NOTHING, db_column='workspaceId')
    projectId = models.ForeignKey(Project, on_delete=models.CASCADE, db_column= 'projectId')
    class Meta:
        managed = False
        db_table = 'WorkerRateSheet'
        constraints = [
            models.UniqueConstraint(fields=['clientId', 'roleId', 'workspaceId'], name='unique_client_role')
        ]

class EqpRateSheet(models.Model):
    _id = models.CharField(primary_key=True, max_length=50, null=False, blank=False)
    clientId = models.ForeignKey(Client, on_delete=models.CASCADE, db_column='clientId', blank=False, null=False)
    equipId = models.ForeignKey(Equipment, on_delete=models.DO_NOTHING, db_column='equipId', blank=False, null=False)
    unitRate = models.DecimalField(max_digits=10, decimal_places=2,blank=True,null=True, default=0.00)
    dayRate = models.DecimalField(max_digits=10, decimal_places=2,blank=True,null=True, default=0.00)
    workspaceId = models.ForeignKey(Workspace, models.DO_NOTHING, db_column='workspaceId')
    projectId = models.ForeignKey(Project, on_delete=models.CASCADE, db_column= 'projectId')
    class Meta:
        managed = False
        db_table = 'EqpRateSheet'
        constraints = [
            models.UniqueConstraint(fields=['clientId', 'equipId', 'workspaceId'], name='unique_client_equip')
        ]

class ClientRep(models.Model):
    _id = models.CharField(primary_key=True, max_length=50, null=False, blank=False)
    empId = models.ForeignKey(Employeeuser, on_delete=models.DO_NOTHING, db_column='empId', blank=False, null=False)
    clientId = models.ForeignKey(Client, on_delete=models.CASCADE, db_column='clientId', blank= False, null=False)
    workspaceId = models.ForeignKey(Workspace, models.DO_NOTHING, db_column='workspaceId')
    class Meta:
        managed = False
        db_table = 'ClientRep'
        constraints = [
            models.UniqueConstraint(fields=['empId', 'clientId', 'workspaceId'], name='unique_client_rep')
        ]

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
