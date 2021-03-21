import json

from django.db.models import Q

import VLE.factory as factory
import VLE.lti1p3 as lti
from VLE.models import Course
from VLE.utils.error_handling import VLEBadRequest


class Lti1p3CourseData(lti.utils.PreparedData):
    def __init__(self, data):
        # TODO LTI: check if it is possible to update the description / title on the Canvas side
        self.data = data
        self.create_keys = [
            'name',
            'abbreviation',
            'startdate',
            'enddate',
            'author',
            'active_lti_id',
            'lms_id',
            'names_role_service',
        ]
        # QUESTION LTI: are these valid settings?
        self.update_keys = [
            'name',
            'abbreviation',
            'startdate',
            'enddate',
            # 'author', TODO: This is currently the user first opening the course. Should be the real author
            # 'active_lti_id',
            'lms_id',
            'names_role_service',
        ]

    @property
    def name(self):
        return self.data[lti.claims.COURSE]['title']

    @property
    def abbreviation(self):
        return self.data[lti.claims.COURSE]['label']

    @property
    def startdate(self):
        return self.data[lti.claims.CUSTOM].get('course_start', None)

    @property
    def enddate(self):
        return self.data[lti.claims.CUSTOM].get('course_end', None)

    @property
    def author(self):
        return lti.user.Lti1p3UserData(self.data).find_in_db()

    @property
    def active_lti_id(self):
        return self.data[lti.claims.COURSE]['id']

    @property
    def lms_id(self):
        return self.data[lti.claims.CUSTOM]['course_id']

    @property
    def names_role_service(self):
        return json.dumps(self.data[lti.claims.NAMESROLES])

    def find_in_db(self):
        return Course.objects.filter(
            Q(active_lti_id=self.active_lti_id) |
            Q(lms_id=self.lms_id)
        ).first()

    def create(self):
        course = factory.make_course(**self.create_dict)
        lti.members.sync_members(course)
        return course

    def update(self, obj=None):
        course = obj
        if not course:
            course = self.find_in_db()

        if course.active_lti_id and course.active_lti_id != self.active_lti_id:
            raise VLEBadRequest('Course already linked to LMS.')

        # TODO LTI: only when new active lti id
        lti.members.sync_members(course)

        for key in self.update_keys:
            if getattr(self, key) is not None:
                setattr(course, key, getattr(self, key))

        course.save()

        return course
