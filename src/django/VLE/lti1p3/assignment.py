# TODO LTI: add test where it first connects assignment from course 1, then  from course 2, then see if course 1 again
# has a valid setup
import json

from dateutil.parser import parse
from django.conf import settings
from pylti1p3.exception import LtiException

import VLE.factory as factory
import VLE.lti1p3 as lti
from VLE.lti1p3 import utils
from VLE.models import Assignment, PresetNode


class AssignmentData(utils.PreparedData):
    model = Assignment
    _connected_course = None
    _author = None

    def create(self):
        if not self.connected_course:
            raise LtiException('Could not find the connected course, please check if the course already exists')

        assignment = factory.make_assignment(**self.create_dict, courses=[self.connected_course])
        # TODO LTI: fix courses[0] when the courses is improved as well
        assignment.add_lti_id(self.active_lti_id, self.connected_course)

        return assignment

    def update(self, obj=None):
        assignment = obj
        if not assignment:
            assignment = self.find_in_db()

        update_keys = self.update_keys
        nodes = PresetNode.objects.filter(format__assignment=assignment)

        # Exclude dates if it is not possible to update
        # TODO LTI: check if the TZ_INFO can be optimized
        first_unlock = nodes.order_by('unlock_date').values('unlock_date').first()
        if first_unlock:
            first_unlock = first_unlock.get('unlock_date', None)
        last_due = nodes.order_by('due_date').values('due_date').first()
        if last_due:
            last_due = last_due.get('due_date', None)
        last_lock = nodes.order_by('lock_date').values('lock_date').first()
        if last_lock:
            last_lock = last_lock.get('lock_date', None)

        if (
            first_unlock and self.unlock_date and
            first_unlock.replace(tzinfo=settings.TZ_INFO) < parse(self.unlock_date)
        ):
            update_keys.remove('unlock_date')
        if (
            last_due and self.due_date and
            last_due.replace(tzinfo=settings.TZ_INFO) > parse(self.due_date)
        ):
            update_keys.remove('due_date')
        if (
            (last_lock and self.lock_date and
             last_lock.replace(tzinfo=settings.TZ_INFO) > parse(self.lock_date)) or
            (last_due and self.lock_date and
             last_due.replace(tzinfo=settings.TZ_INFO) > parse(self.lock_date))
        ):
            update_keys.remove('lock_date')

        # Exclude published state if it is not possible to update
        if not assignment.can_be_unpublished():
            update_keys.remove('is_published')

        for key in update_keys:
            # assignments_grades_service we DO want to update even when None
            # This is for the cases where we switch from LTI 1.3 to an LTI 1.0 assignment
            if getattr(self, key) is not None or key == 'assignments_grades_service':
                setattr(assignment, key, getattr(self, key))

        # TODO LTI: only update if sth actually changed (also for course & user)
        assignment.save()

        if self.connected_course:
            # add_course already checks that a course wont be added twice, no need to do it here
            assignment.add_course(self.connected_course)

        # TODO LTI: indication that the user needs to REVISIT the assignment from the new
        # Canvas course after he switched from LTI course.

        return assignment

    def find_in_db(self, *args, **kwargs):
        assignment = super().find_in_db(*args, **kwargs)
        if assignment:
            return assignment

        # If it is not found by the default find keys, also check if the lti_id_set contains the active lti id
        # This is useful when an assignment is linked to multiple courses, with only the other assignment as active
        assignment = Assignment.objects.filter(lti_id_set__contains=[self.active_lti_id]).first()

        return assignment


class Lti1p3AssignmentData(AssignmentData):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.create_keys = [
            'name',
            'author',
            'active_lti_id',
            'points_possible',
            'is_published',
            'unlock_date',
            'due_date',
            'lock_date',
            'assignments_grades_service',
        ]
        # QUESTION LTI: are these valid settings?
        self.update_keys = [
            'name',
            # 'author', TODO: This is currently the user first opening the course. Should be the real author
            # 'active_lti_id',
            # 'points_possible',
            'is_published',
            'unlock_date',
            'due_date',
            'lock_date',
            'assignments_grades_service',
        ]
        self.find_keys = [
            'active_lti_id',
        ]

    @property
    def name(self):
        return self.to_str(self.data[lti.claims.ASSIGNMENT]['title'])

    @property
    def author(self):
        if not self._author:
            self._author = lti.user.Lti1p3UserData(self.data).find_in_db()

        return self._author

    @property
    def active_lti_id(self):
        # We use the custom set variable here because in the gradebook the CONTEXT lti_id is different
        return self.to_str(self.data[lti.claims.CUSTOM]['assignment_lti_id'])

    @property
    def points_possible(self):
        return self.to_float(self.data[lti.claims.CUSTOM]['assignment_points'])

    @property
    def is_published(self):
        return self.to_bool(self.data[lti.claims.CUSTOM]['assignment_publish'])

    @property
    def unlock_date(self):
        return self.to_datetime(self.data[lti.claims.CUSTOM].get('assignment_unlock', None))

    @property
    def due_date(self):
        return self.to_datetime(self.data[lti.claims.CUSTOM].get('assignment_due', None))

    @property
    def lock_date(self):
        return self.to_datetime(self.data[lti.claims.CUSTOM].get('assignment_lock', None))

    @property
    def connected_course(self):
        if not self._connected_course:
            self._connected_course = lti.course.Lti1p3CourseData(self.data).find_in_db()

        return self._connected_course

    @property
    def assignments_grades_service(self):
        return json.dumps(self.data[lti.claims.ASSIGNMENTSGRADES])


class Lti1p0AssignmentData(AssignmentData):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # TODO LTI: check if it is possible to update the description / title on the Canvas side
        self.create_keys = [
            'name',
            'author',
            'active_lti_id',  # NOTE: we use active_lti_id for both LTI 1.0 and LTI 1.3 as they cannot coincide
            'points_possible',
            'is_published',
            'unlock_date',
            'due_date',
            'lock_date',
            'assignments_grades_service',
        ]
        # QUESTION LTI: are these valid settings?
        self.update_keys = [
            'name',
            # 'author', TODO: This is currently the user first opening the course. Should be the real author
            # 'active_lti_id',
            # 'points_possible',
            'is_published',
            'unlock_date',
            'due_date',
            'lock_date',
            # NOTE: we also update the assignments_grades_service because when switching from LTI 1.3 to LTI 1.0, we
            # do not want to keep the LTI 1.3 information left in the assignment. It can be re-added later when
            # switching back to LTI 1.3
            'assignments_grades_service',
        ]
        self.find_keys = [
            'active_lti_id',
        ]

    @property
    def name(self):
        return self.to_str(self.data['custom_assignment_title'])

    @property
    def author(self):
        if not self._author:
            self._author = lti.user.Lti1p0UserData(self.data).find_in_db()

        return self._author

    @property
    def active_lti_id(self):
        return self.to_str(self.data['custom_assignment_id'])

    @property
    def points_possible(self):
        return self.to_float(self.data.get('custom_assignment_points', None))

    @property
    def is_published(self):
        return self.to_bool(self.data.get('assignment_publish', True))

    @property
    def unlock_date(self):
        return self.to_datetime(self.data.get('custom_assignment_unlock', None))

    @property
    def due_date(self):
        return self.to_datetime(self.data.get('custom_assignment_due', None))

    @property
    def lock_date(self):
        return self.to_datetime(self.data.get('custom_assignment_lock', None))

    @property
    def connected_course(self):
        if not self._connected_course:
            self._connected_course = lti.course.Lti1p0CourseData(self.data).find_in_db()

        return self._connected_course

    @property
    def assignments_grades_service(self):
        return None
