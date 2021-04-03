import json

from django.conf import settings

import VLE.factory as factory
import VLE.lti1p3 as lti
from VLE.models import Course
from VLE.utils.error_handling import VLEBadRequest


class CourseData(lti.utils.PreparedData):
    model = Course
    _author = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.debug_keys = []

    def create(self, sync_members=True, create_paticipation=True):
        if self.find_in_db():
            raise VLEBadRequest('Course already exists')
        course = factory.make_course(**self.create_dict())

        if sync_members:
            lti.members.sync_members(course)

        if create_paticipation:
            if settings.LTI13 in course.lti_versions:
                lti.user.Lti1p3UserData(self.data).create_or_update_participation(course=course)
            else:
                lti.user.Lti1p0UserData(self.data).create_or_update_participation(course=course)

        return course

    def update(self, obj=None):
        course = obj
        if not course:
            course = self.find_in_db()

        if (
            # LTI 1.3
            hasattr(self, 'lti_id') and course.lti_id and course.lti_id != self.lti_id
            # LTI 1.0
            or hasattr(self, 'lms_id') and course.lms_id and course.lms_id != self.lms_id
        ):
            raise VLEBadRequest('Course already linked to LMS.')

        # Only sync members when there is a change in LTI 1.3 course
        if hasattr(self, 'lti_id') and course.lti_id != self.lti_id:
            lti.members.sync_members(course)

        changed = False
        for key in self.update_keys:
            if getattr(self, key) is not None:
                changed = True
                setattr(course, key, getattr(self, key))

        if changed:
            course.save()

        return course


class Lti1p3CourseData(CourseData):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.create_keys = [
            'name',
            'abbreviation',
            'startdate',
            'enddate',
            'author',
            'lti_id',
            'lms_id',
            'names_role_service',
        ]
        # QUESTION LTI: are these valid settings?
        self.update_keys = [
            'name',
            'abbreviation',
            'startdate',
            'enddate',
            # 'author',
            # 'lti_id',
            'lms_id',
            'names_role_service',
        ]
        self.find_keys = [
            'lti_id',
            'lms_id',
        ]

    @property
    def name(self):
        return self.to_str(self.data[lti.claims.COURSE]['title'])

    @property
    def abbreviation(self):
        return self.to_str(self.data[lti.claims.COURSE]['label'])

    @property
    def startdate(self):
        return self.to_datetime(self.data[lti.claims.CUSTOM].get('course_start', None))

    @property
    def enddate(self):
        return self.to_datetime(self.data[lti.claims.CUSTOM].get('course_end', None))

    @property
    def author(self):
        if not self._author:
            course = self.find_in_db()
            # If course already exists, that should also be the author
            if course and course.author:
                self._author = course.author
            else:
                # If it doesnt exists, consider the user in the dataparams as the author
                # IFF the user has a teacher role
                # NOT if the user is already a teacher, as a platform teacher from 1 course
                # does not have to be a teacher in this course
                # TODO LTI: platform wide teachers are still considered teacher. This should not be the case
                user_data = lti.user.Lti1p3UserData(self.data)
                if user_data.role_name == 'Teacher':
                    self._author = user_data.find_in_db()

        return self._author

    @property
    def lti_id(self):
        return self.to_str(self.data[lti.claims.COURSE]['id'])

    @property
    def lms_id(self):
        return self.to_str(self.data[lti.claims.CUSTOM]['course_id'])

    @property
    def names_role_service(self):
        return json.dumps(self.data[lti.claims.NAMESROLES])


class Lti1p0CourseData(CourseData):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.create_keys = [
            'name',
            'abbreviation',
            'startdate',
            'enddate',
            'author',
            'lms_id',
        ]
        # QUESTION LTI: are these valid settings?
        self.update_keys = [
            'name',
            'abbreviation',
            'startdate',
            'enddate',
            # 'author',
            # 'lms_id',
        ]
        self.find_keys = [
            'lms_id'
        ]

    @property
    def name(self):
        return self.to_str(self.data['custom_course_name'])

    @property
    def abbreviation(self):
        return self.to_str(self.data.get('context_label', None))

    @property
    def startdate(self):
        return self.to_datetime(self.data.get('custom_course_start', None))

    @property
    def enddate(self):
        return self.to_datetime(self.data.get('custom_course_end', None))

    @property
    def author(self):
        if not self._author:
            course = self.find_in_db()
            # If course already exists, that should also be the author
            if course:
                self._author = course.author
            else:
                # If it doesnt exists, consider the user in the dataparams as the author
                # IFF the user has a teacher role
                # NOT if the user is already a teacher, as a platform teacher from 1 course
                # does not have to be a teacher in this course
                # TODO LTI: platform wide teachers are still considered teacher. This should not be the case
                user_data = lti.user.Lti1p0UserData(self.data)
                if user_data.role_name == 'Teacher':
                    self._author = user_data.find_in_db()

        return self._author

    @property
    def lms_id(self):
        return self.to_str(self.data['custom_course_id'])
