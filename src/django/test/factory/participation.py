import factory

import VLE.factory
import VLE.models

import test.factory.assignment


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

    # TODO JIR: restore and delete set_assignment once journalfactory can pass
    # its own assignment via the ap related factory.
    # assignment = factory.SubFactory('test.factory.assignment.AssignmentFactory')
    # assignment = None

    # @factory.post_generation
    # def set_assignment(self, create, extracted):
    #     if not create:
    #         return

    #     if extracted:
    #         self.assignment = extracted
    #     elif self.journal:
    #         self.assignment = self.journal.assignment
    #     else:
    #         self.assignment = test.factory.assignment.AssignmentFactory()

    #     self.save()

    @factory.post_generation
    def add_user_to_missing_courses(self, create, extracted):
        if not create:
            return

        for course in self.assignment.courses.all():
            if not VLE.models.Participation.objects.filter(course=course, user=self.user).exists():
                role = VLE.models.Role.objects.get(course=course, name='Student')
                ParticipationFactory(course=course, user=self.user, role=role)


class LtiAssignmentParticipationFactory(AssignmentParticipationFactory):
    grade_url = 'https://www.ejournal.app/'
    sourcedid = 'Not None'
