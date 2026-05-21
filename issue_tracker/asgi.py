"""
ASGI config for issue_tracker project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

from issue_tracker.bootstrap import setup_path

setup_path()

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'issue_tracker.settings')

application = get_asgi_application()
