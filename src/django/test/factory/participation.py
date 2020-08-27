import test.factory

import factory
import VLE.models


class ParticipationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'VLE.Participation'

    user = factory.SubFactory('test.factory.user.UserFactory')
    course = factory.SubFactory('test.factory.course.CourseFactory')
    role = factory.SubFactory('test.factory.role.RoleFactory', course=factory.SelfAttribute('..course'))

    @factory.post_generation
    def group(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted and isinstance(extracted, list):
            if all(isinstance(obj, VLE.models.Group) for obj in extracted):
                self.groups.set(extracted)
        elif isinstance(extracted, VLE.models.Group):
            self.groups.add(extracted)
        elif kwargs:
            test.factory.Group(**{**kwargs, 'course': self.course})


class AssignmentParticipationFactory(factory.django.DjangoModelFactory):
    '''
    Generates an assignment participation. Will add the provided user to all the assignment's courses via default
    participations.

    Default yields:
        - User: Student user
        - Assignment and via upwards chain course.
        - Lti trait can be activitated as factory.AssignmentParticipation(lti=True)
    '''
    class Meta:
        model = 'VLE.AssignmentParticipation'

    class Params:
        lti = factory.Trait(
            grade_url='https://www.ejournal.app/',
            sourcedid='Not None'
        )

    user = factory.SubFactory('test.factory.user.UserFactory')
    assignment = factory.SubFactory('test.factory.assignment.AssignmentFactory')

    @factory.post_generation
    def add_user_to_missing_courses(self, create, extracted):
        if not create:
            return

        for course in self.assignment.courses.all():
            if not VLE.models.Participation.objects.filter(course=course, user=self.user).exists():
                role = VLE.models.Role.objects.get(course=course, name='Student')
                ParticipationFactory(course=course, user=self.user, role=role)
