
from __future__ import absolute_import, unicode_literals
import os
import logging 
from celery import Celery


# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'HpClockfiyApi.settings')

app = Celery('HpClockfiyApi', broker= 'amqp://guest:guest@localhost', backend='rpc://')

app.control.purge()


# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

