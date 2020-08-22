import factory

import VLE.factory
import VLE.models


class ParticipationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'VLE.Participation'

    user = factory.SubFactory('test.factory.user.UserFactory')
    course = factory.SubFactory('test.factory.course.CourseFactory')
    role = factory.SubFactory('test.factory.role.RoleFactory', course=factory.SelfAttribute('..course'))


class GroupParticipationFactory(ParticipationFactory):
    group = factory.SubFactory('test.factory.group.GroupFactory')


class AssignmentParticipationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'VLE.AssignmentParticipation'

    user = factory.SubFactory('test.factory.user.UserFactory')
    assignment = factory.SubFactory('test.factory.assignment.AssignmentFactory')

    @factory.post_generation
    def add_user_to_assignment(self, create, extracted):
        if not create:
            return

        if not VLE.models.Participation.objects.filter(
           course__in=self.assignment.courses.all(), user=self.user).exists():
            for course in self.assignment.courses.all():
                if not VLE.models.Participation.objects.filter(course=course, user=self.user).exists():
                    role = VLE.models.Role.objects.get(course=course, name='Student')
                    VLE.models.Participation.objects.create(course=course, user=self.user, role=role)
