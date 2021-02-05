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


@shared_task
def generate_new_comment_notifications(comment_id):
    comment = VLE.models.Comment.objects.select_related('entry__node__journal', 'author').get(pk=comment_id)

    # Generate notifications for supervisors even when commenter is not student
    for user in VLE.permissions.get_supervisors_of(comment.entry.node.journal).exclude(pk=comment.author.pk):
        VLE.models.Notification.objects.create(
            type=VLE.models.Notification.NEW_COMMENT,
            user=user,
            comment=comment,
        )

    # Generate notifications for all other students in journal
    for author in comment.entry.node.journal.authors.all().exclude(user=comment.author):
        VLE.models.Notification.objects.create(
            type=VLE.models.Notification.NEW_COMMENT,
            user=author.user,
            comment=comment,
        )


@shared_task
def generate_new_entry_notifications(entry_id, node_id):
    entry = VLE.models.Entry.objects.select_related(
        'node', 'node__journal', 'node__journal__assignment').get(pk=entry_id)
    if not hasattr(entry, 'node'):
        # NOTE: this query is needed because of the limitations in factory boy
        # see UnlimitedEntryFactory.fix_node
        entry.node = VLE.models.Node.objects.select_related('journal', 'journal__assignment').get(pk=node_id)

    for user in VLE.permissions.get_supervisors_of(entry.node.journal):
        VLE.models.Notification.objects.create(
            type=VLE.models.Notification.NEW_ENTRY,
            user=user,
            entry=entry,
        )
