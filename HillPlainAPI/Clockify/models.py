from django.db import models
from asgiref.sync import sync_to_async
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
    end_date = models.DateField(blank=True, null=True)
    hourly = models.IntegerField(blank = True, null = True, default = 0, db_column = 'hourly')
    Truck = models.IntegerField(blank= False, null = True, default=0, db_column='hasTruck')
    truckDetails = models.CharField(blank= True, null= True, db_column= 'truckDetails', max_length=50)
    class Meta:
        managed = False
        db_table = 'EmployeeUser'

    def __str__(self):
        return self.name or ""
    
    async def asave(self):
        """
        Custom method to asynchronously save a model instance using a serializer.
        """
        if self.instance:  # If it's an existing instance (update)
            await sync_to_async(self.instance.save)()
        else:  # If it's a new instance (insert)
            await sync_to_async(self.save)()
    
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
    task = models.CharField(max_length=200, blank=True, null=True)
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

class Holidays(models.Model):
    id = models.CharField(max_length=50, primary_key= True)
    date = models.DateField(blank=True, null=True)
    name = models.CharField(max_length=100, blank=False, null=False)
    class Meta: 
        managed = False
        db_table = 'Holidays'
    def __str__(self):
        return self.name + ":" + f" {self.date.isoformat()}" or ""
    
class BackGroundTaskResult(models.Model):
    status_code = models.IntegerField(default=404)
    message = models.TextField(blank=True, null= True)
    data = models.TextField(blank=False, null=False )
    time = models.DateTimeField(blank=False, null=False)
    caller = models.CharField(max_length=50 )
    class Meta:
        managed = False
        db_table = 'BackGroundTaskDjango'
