import test.factory.role

import factory

import VLE.models


class CourseFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'VLE.Course'

    name = 'Academische Vaardigheden 1'
    abbreviation = "AVI1"
    startdate = factory.Faker('date_between', start_date="-10y", end_date="-1y")
    enddate = factory.Faker('date_between', start_date="+1y", end_date="+10y")

    student_role = factory.RelatedFactory('test.factory.role.StudentRoleFactory', 'course')
    ta_role = factory.RelatedFactory('test.factory.role.TaRoleFactory', 'course')
    author = factory.SubFactory('test.factory.user.TeacherFactory')

    @factory.post_generation
    def ensure_author_is_course_teacher(self, create, extracted):
        if not create:
            return

        if not VLE.models.Participation.objects.filter(user=self.author, course=self).exists():
            role = test.factory.role.TeacherRoleFactory(course=self)
            participation = VLE.models.Participation(course=self, user=self.author, role=role)
            participation.save()


class LtiCourseFactory(CourseFactory):
    active_lti_id = factory.Sequence(lambda x: "course_lti_id{}".format(x))
    author = factory.SubFactory('test.factory.user.LtiTeacherFactory')
