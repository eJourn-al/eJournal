from __future__ import absolute_import, unicode_literals

from celery import shared_task

import VLE.models


@shared_task
def generate_new_node_notifications(node_ids):
    for node_id in node_ids:
        node = VLE.models.Node.objects.get(pk=node_id)
        for author in node.journal.authors.all():
            if author.user.can_view(node.journal):
                VLE.models.Notification.objects.create(
                    type=VLE.models.Notification.NEW_NODE,
                    user=author.user,
                    node=node,
                )
