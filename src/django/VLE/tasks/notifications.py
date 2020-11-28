from __future__ import absolute_import, unicode_literals

from celery import shared_task

import VLE.models


@shared_task
def generate_new_assignment_notifications(ap_ids):
    aps = VLE.models.AssignmentParticipation.objects.filter(pk__in=ap_ids)
    for ap in aps:
        ap.create_new_assignment_notification()


@shared_task
def generate_new_node_notifications(node_ids):
    nodes = VLE.models.Node.objects.filter(pk__in=node_ids)
    for node in nodes:
        for author in node.journal.authors.all():
            if author.user.can_view(node.journal):
                VLE.models.Notification.objects.create(
                    type=VLE.models.Notification.NEW_NODE,
                    user=author.user,
                    node=node,
                )
