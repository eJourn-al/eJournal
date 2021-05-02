import json
import xml.etree.cElementTree as ET

import oauth2
from celery import shared_task
from django.conf import settings
from pylti1p3.assignments_grades import AssignmentsGradesService
from pylti1p3.grade import Grade
from pylti1p3.service_connector import ServiceConnector

from VLE.models import AssignmentParticipation, Counter, Instance, Journal


class GradePassBackRequest(object):
    """Class to send Grade replace lti requests."""

    def __init__(self, e_grade):
        """
        Create the instance to set the needed variables.

        Arguments:
        key -- key for the oauth communication
        secret -- secret for the oauth communication
        author -- journal author (AssignmentParticipation)
        """
        self.key = settings.LTI_KEY
        self.secret = settings.LTI_SECRET

        self.e_grade = e_grade

        self.url = str(e_grade.get_grade_url())
        self.sourcedid = str(e_grade.get_sourcedid())
        self.timestamp = str(e_grade.get_timestamp())
        self.author = e_grade.get_author()
        self.score = str(e_grade.get_score_percentage())
        self.result_data = e_grade.get_result_data()

    @classmethod
    def get_message_id_and_increment(cls):
        """Get the current count for message_id and increment this count."""
        message_id_counter = Counter.objects.get_or_create(name='message_id')[0]
        count = message_id_counter.count
        message_id_counter.count += 1
        message_id_counter.save()
        return str(count)

    def create_xml(self):
        """Create the xml used as the body of the lti communication."""
        root = ET.Element(
            'imsx_POXEnvelopeRequest',
            xmlns='http://www.imsglobal.org/services/ltiv1p1/xsd/imsoms_v1p0'
        )
        head = ET.SubElement(root, 'imsx_POXHeader')
        head_info = ET.SubElement(head, 'imsx_POXRequestHeaderInfo')
        imsx_version = ET.SubElement(head_info, 'imsx_version')
        imsx_version.text = 'V1.0'
        msg_id = ET.SubElement(head_info, 'imsx_messageIdentifier')
        msg_id.text = GradePassBackRequest.get_message_id_and_increment()
        body = ET.SubElement(root, 'imsx_POXBody')
        request = ET.SubElement(body, 'replaceResultRequest')

        if self.timestamp is not None:
            submission_details = ET.SubElement(request, 'submissionDetails')
            timestamp = ET.SubElement(submission_details, 'submittedAt')
            timestamp.text = self.timestamp

        result_record = ET.SubElement(request, 'resultRecord')
        sourced_guid = ET.SubElement(result_record, 'sourcedGUID')
        sourced_id = ET.SubElement(sourced_guid, "sourcedId")
        sourced_id.text = self.sourcedid

        if self.e_grade.send_score or self.result_data:
            result = ET.SubElement(result_record, 'result')

        if self.e_grade.send_score:
            result_score = ET.SubElement(result, 'resultScore')
            language = ET.SubElement(result_score, 'language')
            language.text = 'en'
            score = ET.SubElement(result_score, 'textString')
            score.text = self.score

        if self.result_data:
            data = ET.SubElement(result, 'resultData')
            if 'url' in self.result_data:
                data_url = ET.SubElement(data, 'url')
                data_url.text = self.result_data['url']
            if 'text' in self.result_data:
                data_text = ET.SubElement(data, 'text')
                data_text.text = self.result_data['text']
            if 'launchUrl' in self.result_data:
                launch_url = ET.SubElement(data, 'ltiLaunchUrl')
                launch_url.text = self.result_data['launchUrl']

        return ET.tostring(root, encoding='utf-8')

    def send_grade_to_lms(self):
        """
        Send the grade replace post request.

        returns response dictionary with status of request
        """
        if self.url is not None and self.sourcedid is not None:
            consumer = oauth2.Consumer(
                self.key, self.secret
            )
            client = oauth2.Client(consumer)
            _, content = client.request(
                self.url,
                'POST',
                body=self.create_xml(),
                headers={'Content-Type': 'application/xml'}
            )
            return {
                'user': self.author.user.username,
                'grade': 'NOT UPDATED' if self.score is None else self.score,
                'result_data': self.result_data,
                **self.parse_return_xml(content),
            }
        return {
            'severity': 'status',
            'code_mayor': 'No grade passback url set',
            'description': 'not found'
        }

    def parse_return_xml(self, xml):
        """
        Parse the xml returned by the lti instance.

        Arguments:
        xml -- response xml as byte literal

        returns response dictionary with status of request
        """
        root = ET.fromstring(xml)
        namespace = root.tag.split('}')[0] + '}'
        head = root.find(namespace + 'imsx_POXHeader')
        imsx_head_info = head.find(namespace + 'imsx_POXResponseHeaderInfo')
        imsx_status_info = imsx_head_info.find(namespace + 'imsx_statusInfo')
        imsx_code_mayor = imsx_status_info.find(namespace + 'imsx_codeMajor')
        if imsx_code_mayor is not None and imsx_code_mayor.text is not None:
            code_mayor = imsx_code_mayor.text
        else:
            code_mayor = None

        imsx_severity = imsx_status_info.find(namespace + 'imsx_severity')
        if imsx_severity is not None and imsx_severity.text is not None:
            severity = imsx_severity.text
        else:
            severity = None

        imsx_description = imsx_status_info.find(
            namespace + 'imsx_description')
        if imsx_description is not None and imsx_description.text is not None:
            description = imsx_description.text
        else:
            description = 'not found'

        return {'severity': severity, 'code_mayor': code_mayor,
                'description': description}


class eGrade(Grade):
    ACTIVITY_PROGRESS = {
        'NO_SUBMISSION': 'Initialized',
        'HAS_SUBMISSIONS': 'Submitted',
        'FINISHED': 'Completed',
    }
    GRADING_PROGRESS = {
        'NO_SUBMISSION': 'NotReady',
        'NEEDS_GRADING': 'PendingManual',
        'DONE_GRADING': 'Pending',
        'FINISHED': 'FullyGraded',
    }
    _result_data = None

    def __init__(self, author, send_score=True, left_journal=False, journal=None):
        # When a student leaves a group journal we still need the group journal
        # Incase the grade should not be reset after leave, we need to access the old journal grade
        if not journal:
            journal = author.journal

        # Journal is not annotated, so annotate it
        if not hasattr(journal, 'grade'):
            journal = Journal.objects.get(pk=journal.pk)

        self._journal = journal
        self._assignment = author.assignment
        self._course = self._assignment.get_active_course(author.user)

        self._author = author
        self.send_score = send_score
        self.left_journal = left_journal

        if left_journal and self._assignment.remove_grade_upon_leaving_group:
            # https://www.imsglobal.org/spec/lti-ags/v2p0#scoregiven-and-scoremaximum
            # > When scoreGiven is null ... the platform should clear any previous score value ... for that user.
            self.set_score_given(None)
        elif send_score:
            self.set_score_maximum(self._assignment.points_possible)
            self.set_score_given(self._journal.grade)

        if self._assignment.is_lti10_version():
            self.init_10(author, send_score=send_score, left_journal=left_journal)

        elif self._assignment.is_lti13_version():
            self.init_13(author, send_score=send_score, left_journal=left_journal)

    def init_13(self, author, send_score=True, left_journal=False):
        submission_data = settings.LTI_LAUNCH_URL
        if not left_journal:
            submission_data += f'?submission={self._journal.pk}'
        else:
            submission_data += f'?left_journal=true'

        self.set_extra_claims({
            'https://canvas.instructure.com/lti/submission':
            {
                'submission_type': 'basic_lti_launch',
                'submission_data': submission_data,
            }
        })

    def init_10(self, author, send_score=True, left_journal=False):
        url = '{0}/Home/Course/{1}/Assignment/{2}'.format(
            settings.BASELINK,
            self._course.pk,
            self._assignment.pk,
        )
        if left_journal:
            # TODO LTI: check what happend to teacher when they recieve such a URL
            url += '?left_journal=true'
        else:
            url += f'/Journal/{self._journal.pk}'

        self._result_data = {
            'url': url
        }

    def get_result_data(self):
        return self._result_data

    def get_author(self):
        return self._author

    def get_score_given(self):
        if self._score_given is None:
            return None

        # QUESTION: we capped at the maximum score for passing back.
        # Do we want to continue this? Or should we also be able to send back higher than max?
        if self._score_given > self.get_score_maximum():
            return self.get_score_maximum()

        return self._score_given

    def get_score_percentage(self):
        if self.get_score_given() is None:
            return None

        return self.get_score_given() / self.get_score_maximum()

    def get_sourcedid(self):
        return self._author.sourcedid

    def get_grade_url(self):
        return self._author.grade_url

    def get_user_id(self):
        if self._assignment.is_lti13_version():
            return self._author.user.lti_1p3_id
        else:
            return self._author.user.lti_1p0_id

    # https://www.imsglobal.org/spec/lti-ags/v2p0#gradingprogress
    def get_grading_progress(self):
        if self.left_journal:
            return self.GRADING_PROGRESS['FINISHED']

        if self._journal.grade is None and not self._journal.node_set.filter(entry__isnull=False).exists():
            return self.GRADING_PROGRESS['NO_SUBMISSION']
        elif self._journal.require_grade_action_nodes.exists():
            # NOTE: With LTI1.3 it either gives teacher a TODO or sets a grade
            # NOTE: Canvas is wrong. NEEDS_GRADING does NOT give a TODO to the teacher, while DONE_GRADING does,
            # although the LTI specification say otherwise
            return self.GRADING_PROGRESS['NEEDS_GRADING']
        else:
            return self.GRADING_PROGRESS['FINISHED']

    # https://www.imsglobal.org/spec/lti-ags/v2p0#activityprogress
    def get_activity_progress(self):
        if self.left_journal:
            return self.GRADING_PROGRESS['NO_SUBMISSION']

        if self._journal.grade is None and not self._journal.node_set.filter(entry__isnull=False).exists():
            return self.ACTIVITY_PROGRESS['NO_SUBMISSION']
        else:
            return self.ACTIVITY_PROGRESS['HAS_SUBMISSIONS']
        # QUESTION: do we ever want to send a "finished" state? this technically should mean that the user
        # is NEVER able to send any update anymore. That said, Canvas does not follow the specifications precicely, and
        # we are still able to send other states after the finished state.

    def get_value(self):
        # type: () -> str
        data = {
            'activityProgress': self.get_activity_progress(),
            'gradingProgress': self.get_grading_progress(),
            'timestamp': self.get_timestamp(),
            'userId': self.get_user_id(),
        }
        if self.send_score:
            data.update({
                'scoreGiven': self.get_score_given(),
                'scoreMaximum': self.get_score_maximum(),
            })
        if self.get_extra_claims() is not None:
            data.update(self.get_extra_claims())

        return json.dumps({k: v for k, v in data.items() if v is not None})


class StudentGrade(eGrade):
    '''Grade information to student'''
    def get_timestamp(self):
        # https://www.imsglobal.org/spec/lti-ags/v2p0#timestamp
        # > A tool MUST NOT send multiple score updates of the same (line item, user) with the same timestamp.
        # QUESTION: what do we want to do with this?
        # It appears that our strategy of just sending the last node was accepted by Canvas, but not
        # accepted by the standard. As we should at least increase the time every time, and for sure cannot go back
        # Same (maybe even more relevant) for teacher timestamp
        if self.left_journal:
            # QUESTION: Currently we keep the timestamp even the same when a student leaves
            # Do we want to change this to reset the grade timestamp to the moment of leaving (i.e. timezone.now())?
            timestamp = self._journal.published_nodes.last().entry.grade.creation_date
        elif self._author.journal.published_nodes:
            timestamp = self._journal.published_nodes.last().entry.grade.creation_date
        else:
            timestamp = self._journal.creation_date
        # TODO LTI: check if this correctly uses timezones
        return timestamp.isoformat()


class TeacherGrade(eGrade):
    '''Grade request to teacher'''
    def get_timestamp(self):
        timestamp = self._journal.require_grade_action_nodes.first().entry.last_edited

        return timestamp.isoformat()


def _get_grades(authors, left_journal=False, journal=None):
    '''Get all the grades with attached the lti version'''
    grades = {}
    for author in authors:
        # Skip asignments without lti link
        if not author.assignment.has_lti_link():
            continue

        is_lti_10 = author.assignment.is_lti10_version()
        if is_lti_10:
            key = settings.LTI10
        else:
            key = author.assignment.assignments_grades_service

        if key not in grades:
            grades[key] = []

        grades[key].append(
            StudentGrade(author, left_journal=left_journal, journal=author.journal or journal)
        )

        # LTI 1.3 cannot have both a todo for teacher and grade for student.
        # This means that (if graded) we only send a todo to the teacher for LTI 1.0
        if is_lti_10 and not left_journal and author.journal.require_grade_action_nodes.exists():
            grades[key].append(
                TeacherGrade(author, send_score=False, left_journal=left_journal, journal=author.journal or journal)
            )

    return grades


@shared_task
def task_send_grade(author_pk=None, author_pks=[], left_journal=False, journal_pk=None):
    return send_grade(
        AssignmentParticipation.objects.filter(pk__in=author_pks + [author_pk]),
        left_journal=left_journal,
        journal=Journal.objects.get(pk=journal_pk) if journal_pk is not None else None,
    )


def send_grade(authors, left_journal=False, journal=None):
    assert not left_journal or journal, 'When a user leaves a journal, journal param should be set'
    grades = _get_grades(authors, left_journal=left_journal, journal=journal)
    result = []
    for lti_10_grade in grades.pop(settings.LTI10, []):
        print('LTI 1.0', lti_10_grade)
        result.append(GradePassBackRequest(lti_10_grade).send_grade_to_lms())

    for grade_service, grades in grades.items():
        print('LTI 1.3', grade_service)
        instance = Instance.objects.get_or_create(pk=1)[0]
        registration = settings.TOOL_CONF.find_registration(instance.iss, client_id=instance.lti_client_id)
        connector = ServiceConnector(registration)
        ags = AssignmentsGradesService(connector, json.loads(grade_service))
        for grade in grades:
            print(grade)
            # TODO LTI: Might raise LtiException when grading goes wrong, handle this
            result.append(ags.put_grade(grade))

    return result
    # TODO LTI: sentry notification when grading fails. And more verbose & alligned (LTI1.1/1.3) responses
    # if not successful:
    #     with push_scope() as scope:
    #         scope.level = 'error'
    #         scope.set_context('data', result)
    #         capture_exception(LmsGradingResponseException('Error on sending grade to LMS'))
