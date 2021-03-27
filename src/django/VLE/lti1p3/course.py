import json

import VLE.factory as factory
import VLE.lti1p3 as lti
from VLE.models import Course
from VLE.utils.error_handling import VLEBadRequest


class CourseData(lti.utils.PreparedData):
    model = Course

    def create(self):
        course = factory.make_course(**self.create_dict)

        lti.members.sync_members(course)

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

        if hasattr(self, 'lti_id') and course.lti_id != self.lti_id:
            lti.members.sync_members(course)

        for key in self.update_keys:
            if getattr(self, key) is not None:
                setattr(course, key, getattr(self, key))

        course.save()

        return course


class Lti1p3CourseData(CourseData):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # TODO LTI: check if it is possible to update the description / title on the Canvas side
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
            # 'author', TODO: This is currently the user first opening the course. Should be the real author
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
        return lti.user.Lti1p3UserData(self.data).find_in_db()

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
            # 'author', TODO: This is currently the user first opening the course. Should be the real author
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
        return lti.user.Lti1p0UserData(self.data).find_in_db()

    @property
    def lms_id(self):
        return self.to_str(self.data.get('custom_course_id', None))
