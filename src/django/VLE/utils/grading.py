
from celery import shared_task
from django.conf import settings
from django.utils import timezone
from sentry_sdk import capture_exception, push_scope

from VLE import factory
from VLE.lti_grade_passback import GradePassBackRequest
from VLE.models import AssignmentParticipation, Comment, Entry, Journal
from VLE.utils.error_handling import LmsGradingResponseException


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

    Entry.objects.filter(node__in=journal.published_nodes).exclude(vle_coupling=Entry.LINK_COMPLETE) \
        .update(vle_coupling=Entry.NEEDS_GRADE_PASSBACK)

    response = {}
    failed = False
    for author in journal.authors.all():
        response[author.id] = send_author_status_to_LMS(journal, author)
        if not response[author.id]['successful']:
            failed = True

    if not failed:
        Entry.objects.filter(node__in=journal.published_nodes).update(vle_coupling=Entry.LINK_COMPLETE)
        Entry.objects.filter(node__in=journal.unpublished_nodes).update(vle_coupling=Entry.SENT_SUBMISSION)

    return {
        'successful': not failed,
        **response,
    }


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

    if author.sourcedid is None:
        return {
            'description': '{} has no sourcedid'.format(author.to_string(user=author.user)),
            'code_mayor': 'error',
            'successful': False,
        }
    if author.grade_url is None:
        return {
            'description': '{} has no grade_url'.format(author.to_string(user=author.user)),
            'code_mayor': 'error',
            'successful': False,
        }

    course = journal.assignment.get_active_course(author.user)
    if not left_journal:
        result_data = {
            'url': '{0}/Home/Course/{1}/Assignment/{2}/Journal/{3}'.format(
                settings.BASELINK, course.pk, journal.assignment.pk, journal.pk)
        }
        grade = journal.grade
    else:
        result_data = {
            'url': '{0}/Home/Course/{1}/Assignment/{2}?left_journal=true'.format(
                settings.BASELINK, course.pk, journal.assignment.pk)
        }
        grade = journal.grade if not journal.assignment.remove_grade_upon_leaving_group else 0

    submitted_at = None

    # Send student latest grade. But only send it when there are new entries OR grade changed
    response_student = None
    if journal.published_nodes.filter(entry__vle_coupling=Entry.NEEDS_GRADE_PASSBACK).exists() or \
       journal.LMS_grade != grade:
        if journal.LMS_grade != grade:
            submitted_at = str(timezone.now())
        else:
            submitted_at = str(journal.published_nodes.last().entry.last_edited)
        # TODO This is reached, now how to show this in a test
        grade_request = GradePassBackRequest(
            author, grade, result_data=result_data, send_score=True, submitted_at=submitted_at)
        response_student = grade_request.send_post_request()
        response_student['old_grade'] = journal.LMS_grade
        response_student['new_grade'] = journal.grade
        if response_student['code_mayor'] == 'success':
            journal.LMS_grade = journal.grade
            journal.save()

    response_teacher = None
    if not left_journal:
        # Notify teacher about last ungraded submission
        if journal.unpublished_nodes.exists():
            result_data = {
                'url': '{0}/Home/Course/{1}/Assignment/{2}/Journal/{3}?nID={4}'.format(
                    settings.BASELINK, course.pk, journal.assignment.pk, journal.pk,
                    journal.unpublished_nodes.first().pk)
            }
            submitted_at = str(journal.unpublished_nodes.first().entry.last_edited)
            grade_request = GradePassBackRequest(
                author, grade, result_data=result_data, send_score=False, submitted_at=submitted_at)
            response_teacher = grade_request.send_post_request()

    successful = (response_teacher is None or response_teacher['code_mayor'] == 'success') and \
        (response_student is None or response_student['code_mayor'] == 'success')
    result = {'to_teacher': response_teacher, 'to_student': response_student}

    if not successful:
        with push_scope() as scope:
            scope.level = 'error'
            scope.set_context('data', result)
            capture_exception(LmsGradingResponseException('Error on sending grade to LMS'))

    return {'successful': successful, **result}
