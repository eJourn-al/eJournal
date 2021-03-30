
from celery import shared_task

from VLE import factory
from VLE.lti1p3 import grading
from VLE.models import AssignmentParticipation, Comment, Entry, Journal


def publish_all_journal_grades(journal, publisher):
    """publish all grades that are not None for a journal.

    - journal: the journal in question
    - publisher: the publisher of the grade
    """
    entries = Entry.objects.filter(node__journal=journal).exclude(grade=None)

    for entry in entries:
        factory.make_grade(entry, publisher.pk, entry.grade.grade, True)

    Comment.objects.filter(entry__node__journal=journal).exclude(entry__grade=None).update(published=True)


@shared_task
def task_bulk_send_journal_status_to_LMS(journal_pks):
    for journal_pk in journal_pks:
        task_journal_status_to_LMS(journal_pk)


@shared_task
def task_journal_status_to_LMS(journal_pk):
    return send_journal_status_to_LMS(Journal.objects.get(pk=journal_pk))


def send_journal_status_to_LMS(journal):
    """Replace a grade on the LTI instance based on the request.

    Arguments:
        journal -- the journal of which the grade needs to be updated through lti.

    returns the lti reponse.
    """
    if not journal.authors.exists():
        return None

    response = {}
    for author in journal.authors.all():
        response[author.id] = send_author_status_to_LMS(journal, author)

    return response


@shared_task
def task_author_status_to_LMS(journal_pk, author_pk, left_journal=False):
    return send_author_status_to_LMS(
        Journal.objects.get(pk=journal_pk), AssignmentParticipation.objects.get(pk=author_pk), left_journal)


def send_author_status_to_LMS(journal, author, left_journal=False):
    """Send the status of about the author of the journal to both the teacher and the author"""
    if author not in journal.authors.all() and not left_journal:
        return {
            'description': '{} not in journal {}'.format(author.user.full_name, journal.to_string()),
            'code_mayor': 'error',
            'successful': False,
        }

    return grading.send_grade(author, left_journal=left_journal, journal=journal)
