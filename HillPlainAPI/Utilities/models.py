from django.db import models


class BackGroundTaskResult(models.Model):
    status_code = models.IntegerField(default=404)
    message = models.TextField(blank=True, null= True)
    data = models.TextField(blank=False, null=False )
    time = models.DateTimeField(blank=False, null=False)
    caller = models.CharField(max_length=50 )
    class Meta:
        managed = False
        db_table = 'BackGroundTaskDjango'

# Create your models here.
