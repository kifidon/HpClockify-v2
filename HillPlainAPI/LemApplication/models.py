from django.db import models
from HillPlainAPI.Clockify.models import Project, Employeeuser, Client, Workspace

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
            models.UniqueConstraint(fields=['clientId', 'roleId', 'workspaceId', 'projectId'], name='unique_client_role')
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
            models.UniqueConstraint(fields=['clientId', 'equipId', 'workspaceId', 'proejctId'], name='unique_client_equip')
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
