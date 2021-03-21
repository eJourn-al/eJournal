import json

from dateutil.parser import parse
from django.conf import settings

import VLE.factory as factory
import VLE.lti1p3 as lti
from VLE.lti1p3 import utils
from VLE.models import Assignment, PresetNode


class Lti1p3AssignmentData(utils.PreparedData):
    def __init__(self, data):
        self.data = data
        # TODO LTI: check if it is possible to update the description / title on the Canvas side
        self.create_keys = [
            'name',
            'description',
            'author',
            'active_lti_id',
            'points_possible',
            'is_published',
            'unlock_date',
            'due_date',
            'lock_date',
            'courses',
            'assignments_grades_service',
        ]
        # QUESTION LTI: are these valid settings?
        self.update_keys = [
            'name',
            'description',
            # 'author', TODO: This is currently the user first opening the course. Should be the real author
            # 'active_lti_id',
            # 'points_possible',
            'is_published',
            'unlock_date',
            'due_date',
            'lock_date',
            # 'courses',  TODO LTI: check how we wanna handle this? Maybe we can just manually add it when linking
            'assignments_grades_service',
        ]

    @property
    def name(self):
        return self.data[lti.claims.ASSIGNMENT]['title']

    @property
    def description(self):
        return self.data[lti.claims.ASSIGNMENT].get('description', None)

    @property
    def author(self):
        return lti.user.Lti1p3UserData(self.data).find_in_db()

    @property
    def active_lti_id(self):
        return self.data[lti.claims.ASSIGNMENT]['id']

    @property
    def points_possible(self):
        return self.data[lti.claims.CUSTOM]['assignment_points']

    @property
    def is_published(self):
        return self.data[lti.claims.CUSTOM]['assignment_publish']

    @property
    def unlock_date(self):
        return self.data[lti.claims.CUSTOM].get('assignment_unlock', None)

    @property
    def due_date(self):
        return self.data[lti.claims.CUSTOM].get('assignment_due', None)

    @property
    def lock_date(self):
        return self.data[lti.claims.CUSTOM].get('assignment_lock', None)

    @property
    def courses(self):
        return [lti.course.Lti1p3CourseData(self.data).find_in_db()]

    @property
    def assignments_grades_service(self):
        return json.dumps(self.data[lti.claims.ASSIGNMENTSGRADES])

    def find_in_db(self):
        return Assignment.objects.filter(active_lti_id=self.active_lti_id).first()

    def create(self):
        return factory.make_assignment(**self.create_dict)

    def update(self, obj=None):
        assignment = obj
        if not assignment:
            assignment = self.find_in_db()

        update_keys = self.update_keys
        nodes = PresetNode.objects.filter(format__assignment=assignment)

        # Exclude dates if it is not possible to update
        if (
            nodes.order_by('unlock_date').first().unlock_date and self.unlock_date and
            nodes.order_by('unlock_date').first().unlock_date.replace(tzinfo=settings.TZ_INFO) <
            parse(self.unlock_date)
        ):
            update_keys.pop('unlock_date', None)
        if (
            nodes.order_by('due_date').last().due_date and self.due_date and
            nodes.order_by('due_date').last().due_date.replace(tzinfo=settings.TZ_INFO) > parse(self.due_date)
        ):
            update_keys.pop('due_date', None)
        if (
            nodes.order_by('lock_date').last().lock_date and self.lock_date and
            nodes.order_by('lock_date').last().lock_date.replace(tzinfo=settings.TZ_INFO) > parse(self.lock_date)
        ):
            update_keys.pop('lock_date', None)
        # Lock date also should not be earlier than last due_date
        if (
            nodes.order_by('due_date').last().due_date and self.lock_date and
            nodes.order_by('due_date').last().due_date.replace(tzinfo=settings.TZ_INFO) > parse(self.lock_date)
        ):
            update_keys.pop('lock_date', None)

        # Exclude published state if it is not possible to update
        if not assignment.can_be_unpublished():
            update_keys.pop('is_published', None)

        for key in update_keys:
            if getattr(self, key) is not None:
                setattr(assignment, key, getattr(self, key))

        assignment.save()

        return assignment
