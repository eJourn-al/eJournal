# Celery tasks
# These are auto discovered via celery.py app.autodiscover_tasks()
# Following the convention:
# - app1/
#     - tasks/
#           - __init__.py import *
#           - taskX.py
#           - taskY.py
#     - models.py
# - app2/
#     - tasks.py
#     - models.py

from .beats.backup import *
from .beats.cleanup import *
from .beats.lti import *
from .beats.notifications import *
from .email import *
