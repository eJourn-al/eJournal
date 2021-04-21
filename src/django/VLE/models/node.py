from django.conf import settings
from django.db import models
from django.db.models.deletion import CASCADE, SET_NULL
from django.utils import timezone

from VLE.tasks.notifications import generate_new_node_notifications
from VLE.utils.error_handling import VLEProgrammingError

from .base import CreateUpdateModel
from .notification import Notification


def CASCADE_IF_UNLIMITED_ENTRY_NODE_ELSE_SET_NULL(collector, field, sub_objs, using):
    # NOTE: Either the function is not yet defined or the node type is not defined.
    # Tag Node.FIELD, update hard coded if changed
    unlimited_entry_nodes = [n for n in sub_objs if n.type == 'e']
    other_nodes = [n for n in sub_objs if n.type != 'e']

    CASCADE(collector, field, unlimited_entry_nodes, using)
    SET_NULL(collector, field, other_nodes, using)


class NodeQuerySet(models.QuerySet):
    def bulk_create(self, nodes, *args, new_node_notifications=True, **kwargs):
        nodes = super().bulk_create(nodes, *args, **kwargs)
        if new_node_notifications:
            generate_new_node_notifications.apply_async(
                args=[[node.pk for node in nodes]],
                countdown=settings.WEBSERVER_TIMEOUT,
            )

        return nodes


class Node(CreateUpdateModel):
    """Node.

    The Node is an Timeline component.
    It can represent many things.
    There are three types of nodes:
    -Progress
        A node that merely is a deadline,
        and contains no entry. This deadline
        contains a 'target point amount'
        which should be reached before the
        due date has passed.
        This type of node has to be predefined in
        the Format. In the Format it is assigned a
        due date and a 'target point amount'.
    -Entry
        A node that is merely an entry,
        and contains no deadline. The entry
        can count toward a total
        'received point amount' which is deadlined
        by one or more Progress nodes.
        This type node can be created by the student
        an unlimited amount of times. It holds one
        of the by format predefined 'global templates'.
    -Entrydeadline
        A node that is both an entry and a deadline.
        This node is entirely separate from the
        Progress and Entry node.
        This type of node has to be predefined in
        the Format. In the Format it is assigned an
        unlock/lock date, a due date and a 'forced template'.
    """
    objects = models.Manager.from_queryset(NodeQuerySet)()

    PROGRESS = 'p'
    ENTRY = 'e'
    ENTRYDEADLINE = 'd'
    ADDNODE = 'a'
    TYPES = (
        (PROGRESS, 'progress'),
        (ENTRY, 'entry'),
        (ENTRYDEADLINE, 'entrydeadline'),
    )

    type = models.TextField(
        max_length=4,
        choices=TYPES,
    )

    entry = models.OneToOneField(
        'Entry',
        null=True,
        on_delete=CASCADE_IF_UNLIMITED_ENTRY_NODE_ELSE_SET_NULL,
    )

    journal = models.ForeignKey(
        'Journal',
        on_delete=models.CASCADE,
    )

    preset = models.ForeignKey(
        'PresetNode',
        null=True,
        on_delete=models.SET_NULL,
    )

    @property
    def is_deadline(self):
        return self.type == self.ENTRYDEADLINE

    @property
    def is_progress(self):
        return self.type == self.PROGRESS

    @property
    def is_entry(self):
        return self.type == self.ENTRY

    @property
    def holds_published_grade(self):
        return self.entry and self.entry.grade and self.entry.grade.grade and self.entry.grade.published

    def open_deadline(self, grade=None):
        """
        Checks if the deadline can be fulfilled

        The due date has not passed and no entry has been submissed or the progress goal has not yet been met.
        """
        if self.is_deadline:
            return not self.entry and self.preset.due_date > timezone.now()

        if self.is_progress:
            if not grade and not hasattr(self.journal, 'grade'):
                raise VLEProgrammingError('Expired deadline check requires a journal grade')

            if grade is None:
                grade = self.journal.grade
            return self.preset.target > grade and self.preset.due_date > timezone.now()

        if self.is_entry:
            return False  # An unlimited entry has no deadline to begin with

        raise VLEProgrammingError('Expired deadline check called on an unsupported node type')

    def to_string(self, user=None):
        return "Node"

    class Meta:
        unique_together = ('preset', 'journal')

    def save(self, *args, **kwargs):
        is_new = self._state.adding

        super(Node, self).save(*args, **kwargs)

        # Create a notification for deadline PresetNodes
        if is_new and self.type in [self.ENTRYDEADLINE, self.PROGRESS]:
            for author in self.journal.authors.all():
                if author.user.can_view(self.journal):
                    Notification.objects.create(
                        type=Notification.NEW_NODE,
                        user=author.user,
                        node=self,
                    )
