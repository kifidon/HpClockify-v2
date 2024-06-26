"""
ASGI config for HpClockfiyApi project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application



os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'HpClockfiyApi.settings')

application = get_asgi_application()


# from channels.routing import get_default_application
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", 'HpClockfiyApi.settings')
# django.setup()
# application = get_default_application()