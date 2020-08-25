from test.factory.participation import ParticipationFactory

import factory

import VLE.models


class CourseFactory(factory.django.DjangoModelFactory):
    '''
    Provides a (:model:`VLE.Course`) instance

    The author generated unless specified and a given (:model:`VLE.Role`) as a Teacher with the expected permissions.
    '''
    class Meta:
        model = 'VLE.Course'

    name = factory.Sequence(lambda x: "Academische Vaardigheden {}".format(x))
    abbreviation = "AVI1"
    startdate = factory.Faker('date_between', start_date="-10y", end_date="-1y")
    enddate = factory.Faker('date_between', start_date="+1y", end_date="+10y")
    author = factory.SubFactory('test.factory.user.TeacherFactory')

    student_role = factory.RelatedFactory('test.factory.role.StudentRoleFactory', factory_related_name='course')
    ta_role = factory.RelatedFactory('test.factory.role.TaRoleFactory', factory_related_name='course')
    teacher_role = factory.RelatedFactory('test.factory.role.TeacherRoleFactory', factory_related_name='course')

    @factory.post_generation
    def ensure_author_is_course_teacher(self, create, extracted):
        if not create:
            return

        if not VLE.models.Participation.objects.filter(user=self.author, course=self).exists():
            role = VLE.models.Role.objects.get(name='Teacher', course=self)
            ParticipationFactory(user=self.author, course=self, role=role)


class LtiCourseFactory(CourseFactory):
    active_lti_id = factory.Sequence(lambda x: "course_lti_id{}".format(x))
    author = factory.SubFactory('test.factory.user.LtiTeacherFactory')
