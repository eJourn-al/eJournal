import json

from django.conf import settings
from django.urls import reverse
from pylti1p3.assignments_grades import AssignmentsGradesService
from pylti1p3.grade import Grade
from pylti1p3.service_connector import ServiceConnector

from VLE.models import Instance


class eGrade(Grade):
    _extra_claims = {}

    def set_extra_claim(self, claim):
        self._extra_claims = {
            **claim,
            **self._extra_claims,
        }

    def get_value(self):
        data = {
            'scoreGiven': int(self._score_given) if self._score_given else None,
            'scoreMaximum': int(self._score_maximum) if self._score_maximum else None,
            'activityProgress': self._activity_progress,
            'gradingProgress': self._grading_progress,
            'timestamp': self._timestamp,
            'userId': self._user_id,
            **self._extra_claims,
        }
        return json.dumps({k: v for k, v in data.items() if v})


# https://www.imsglobal.org/spec/lti-ags/v2p0#gradingprogress
class GradeProgress(object):
    # TODO LTI: add finished states
    NO_SUBMISSION = 'NotReady'
    NEEDS_GRADING = 'PendingManual'
    DONE_GRADING = 'Pending'
    FINISHED = 'FullyGraded'

    @classmethod
    def get_grade_progress(cls, journal):
        if journal.grade is None and not journal.node_set.filter(entry__isnull=False).exists():
            return cls.NO_SUBMISSION
        elif journal.unpublished_nodes.exists():
            return cls.NEEDS_GRADING
        else:
            return cls.FINISHED


# https://www.imsglobal.org/spec/lti-ags/v2p0#activityprogress
class ActivityProgress(object):
    # TODO LTI: add finished states
    NO_SUBMISSION = 'Initialized'
    HAS_SUBMISSIONS = 'Submitted'
    FINISHED = 'Completed'

    @classmethod
    def get_activity_progress(cls, journal):
        if journal.grade is None and not journal.node_set.filter(entry__isnull=False).exists():
            return cls.NO_SUBMISSION
        else:
            return cls.FINISHED


def send_grade(assignment_participation, ags=None):
    instance = Instance.objects.get(pk=1)

    journal = assignment_participation.journal
    assignment = journal.assignment
    assignment.get_active_course(assignment_participation.user)
    user = assignment_participation.user
    timestamp = journal.creation_date
    if journal.published_nodes:
        timestamp = journal.published_nodes.last().entry.last_edited

    grade = eGrade()

    if not ags:
        registration = settings.TOOL_CONF.find_registration(instance.iss, client_id=instance.lti_client_id)
        connector = ServiceConnector(registration)
        ags = AssignmentsGradesService(connector, json.loads(assignment.assignments_grades_service))

    # TODO LTI: change local IP to own IP
    print(timestamp.strftime('%Y-%m-%dT%H:%M:%S+00:00'))
    grade.set_score_given(journal.grade)
    grade.set_score_maximum(assignment.points_possible)
    grade.set_timestamp(timestamp.strftime('%Y-%m-%dT%H:%M:%S+00:00'))
    grade.set_grading_progress(GradeProgress.get_grade_progress(journal))
    grade.set_activity_progress(ActivityProgress.get_activity_progress(journal))
    grade.set_user_id(user.lti_id)
    grade.set_extra_claim({
        'https://canvas.instructure.com/lti/submission':
            {
                'submission_type': 'basic_lti_launch',
                'submission_data': '{base}?submission={submission}'.format(
                    base=reverse('lti_launch'),
                    submission=journal.pk,
                ),
            }
    })
    print(grade.get_value())
    return ags.put_grade(grade)
