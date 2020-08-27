from __future__ import absolute_import, unicode_literals

import VLE.models
import VLE.utils
from celery import shared_task


@shared_task
def check_if_need_VLE_publish():
    for journal in VLE.models.Journal.objects.all():
        VLE.utils.grading.send_journal_status_to_LMS(journal)
