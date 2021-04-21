from django.core.exceptions import ValidationError
from django.db import models
from django.dispatch import receiver
from django.utils import timezone

import VLE.permissions
from VLE.utils.generic_utils import gen_url

from .base import CreateUpdateModel
from .entry import Entry
from .journal import Journal
from .notification import Notification


class JournalImportRequest(CreateUpdateModel):
    """
    Journal Import Request (JIR).
    Stores a single request to import all entries of a journal (source) into another journal (target).

    Attributes:
        source (:model:`VLE.journal`): The journal from which entries will be copied
        target (:model:`VLE.journal`): The journal into which entries will be copied
        author (:model:`VLE.user`): The user who created the journal import request
        state: State of the JIR
        processor (:model:`VLE.user`): The user who updated the JIR state
    """

    PENDING = 'PEN'
    DECLINED = 'DEC'
    APPROVED_INC_GRADES = 'AIG'
    APPROVED_EXC_GRADES = 'AEG'
    APPROVED_WITH_GRADES_ZEROED = 'AWGZ'
    EMPTY_WHEN_PROCESSED = 'EWP'
    APPROVED_STATES = {APPROVED_INC_GRADES, APPROVED_EXC_GRADES, APPROVED_WITH_GRADES_ZEROED}
    STATES = (
        (PENDING, 'Pending'),
        (DECLINED, 'Declined'),
        (APPROVED_INC_GRADES, 'Approved including grades'),
        (APPROVED_EXC_GRADES, 'Approved excluding grades'),
        (APPROVED_WITH_GRADES_ZEROED, 'Approved with all grades set to zero'),
        (EMPTY_WHEN_PROCESSED, 'Empty when processed')
    )

    state = models.CharField(
        max_length=4,
        choices=STATES,
        default=PENDING,
    )
    source = models.ForeignKey(
        'journal',
        related_name='import_request_sources',
        blank=True,
        null=True,
        on_delete=models.SET_NULL
    )
    target = models.ForeignKey(
        'journal',
        related_name='import_request_targets',
        blank=True,
        null=True,
        on_delete=models.CASCADE
    )
    author = models.ForeignKey(
        'user',
        related_name='jir_author',
        blank=True,
        null=True,
        on_delete=models.SET_NULL
    )
    processor = models.ForeignKey(
        'user',
        related_name='jir_processor',
        blank=True,
        null=True,
        on_delete=models.SET_NULL
    )

    def get_update_response(self):
        responses = {
            self.DECLINED: 'The journal import request has been successfully declined.',
            self.APPROVED_INC_GRADES:
                'The journal import request has been successfully approved including all previous grades.',
            self.APPROVED_EXC_GRADES:
                'The journal import request has been successfully approved excluding all previous grades.',
            self.APPROVED_WITH_GRADES_ZEROED:
                """The journal import request has been successfully approved,
                and all of the imported entries have been locked (by setting their respective grades to zero).""",
            self.EMPTY_WHEN_PROCESSED:
                'The source journal no longer has entries to import, the request has been archived.',
        }

        return responses[self.state]

    def target_url(self):
        return gen_url(journal=self.target)

    def source_url(self):
        return gen_url(journal=self.source)

    @receiver(models.signals.pre_delete, sender=Journal)
    def delete_pending_jirs_on_source_deletion(sender, instance, **kwargs):
        JournalImportRequest.objects.filter(source=instance, state=JournalImportRequest.PENDING).delete()

    def save(self, *args, **kwargs):
        is_new = self._state.adding

        super().save(*args, **kwargs)

        if is_new:
            if self.target and self.source and self.state == self.PENDING:
                for user in VLE.permissions.get_supervisors_of(
                        self.target, with_permissions=['can_manage_journal_import_requests']):
                    Notification.objects.create(
                        user=user,
                        type=Notification.NEW_JOURNAL_IMPORT_REQUEST,
                        jir=self,
                    )
        if self.state != self.PENDING:
            Notification.objects.filter(jir=self, sent=False).delete()


@receiver(models.signals.pre_save, sender=JournalImportRequest)
def validate_jir_before_save(sender, instance, **kwargs):
    if instance.target:
        if instance.target.assignment.lock_date and instance.target.assignment.lock_date < timezone.now():
            raise ValidationError('You are not allowed to create an import request for a locked assignment.')
        if instance.state == JournalImportRequest.PENDING and not instance.target.assignment.is_published:
            raise ValidationError('You are not allowed to create an import request for an unpublished assignment.')

    if instance.source:
        if not Entry.objects.filter(node__journal=instance.source).exists():
            raise ValidationError('You cannot create an import request from a journal with no entries.')

    if instance.target and instance.source:
        if instance.source.assignment.pk == instance.target.assignment.pk:
            raise ValidationError('You cannot import a journal into itself.')

        existing_import_qry = instance.target.import_request_targets.filter(
            state__in=JournalImportRequest.APPROVED_STATES, source=instance.source)
        if instance.pk:
            existing_import_qry = existing_import_qry.exclude(pk=instance.pk)
        if existing_import_qry.exists():
            raise ValidationError('You cannot import the same journal multiple times.')
