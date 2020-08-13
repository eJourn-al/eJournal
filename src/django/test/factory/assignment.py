import datetime
import test.factory

import factory
from django.utils import timezone

from VLE.models import Participation, Role, User


def _add_courses(self, create, extracted, **kwargs):
    if extracted or extracted == []:
        for course in extracted:
            self.add_course(course)
    else:
        self.courses.add(test.factory.course.CourseFactory())


class AssignmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'VLE.Assignment'

    name = factory.Sequence(lambda x: "Assignment_{}".format(x))
    description = 'Logboek for all your logging purposes'
    is_published = True
    unlock_date = timezone.now()
    due_date = timezone.now() + datetime.timedelta(weeks=1)
    lock_date = timezone.now() + datetime.timedelta(weeks=2)
    is_group_assignment = False
    can_set_journal_name = False
    can_set_journal_image = False
    can_lock_journal = False
    points_possible = 10

    format = factory.SubFactory('test.factory.format.FormatFactory')

    @factory.post_generation
    def courses(self, create, extracted, **kwargs):
        if not create:
            return

        _add_courses(self, create, extracted, **kwargs)

    @factory.post_generation
    def author(self, create, extracted, **kwargs):
        if not create:
            return

        if isinstance(extracted, User):
            self.author = extracted
        elif kwargs:
            self.author = test.factory.user.UserFactory(**kwargs)
        else:
            if self.courses.exists():
                self.author = self.courses.first().author
            else:
                self.author = test.factory.user.UserFactory()
        self.save()

    @factory.post_generation
    def templates(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted or extracted == []:
            for template in extracted:
                if not template.format.pk == self.format.pk:
                    old_format = template.format
                    template.format = self.format
                    template.save()
                    old_format.delete()
        else:
            test.factory.template.TextTemplateFactory(format=self.format)
            test.factory.template.ColloquiumTemplateFactory(format=self.format)

    @factory.post_generation
    def make_author_teacher_in_all_courses(self, create, extracted, **kwargs):
        if not create or extracted is False:
            return

        for course in self.courses.all():
            if not Participation.objects.filter(course=course, user=self.author).exists():
                teacher_role = Role.objects.get(course=course, name='Teacher')
                test.factory.participation.ParticipationFactory(course=course, user=self.author, role=teacher_role)


class LtiAssignmentFactory(AssignmentFactory):
    active_lti_id = factory.Sequence(lambda x: "assignment_lti_id{}".format(x))

    @factory.post_generation
    def courses(self, create, extracted, **kwargs):
        if not create:
            return

        _add_courses(self, create, extracted, **kwargs)

        for course in self.courses.all():
            course.assignment_lti_id_set.append(self.active_lti_id)
            course.save()


class GroupAssignmentFactory(AssignmentFactory):
    is_group_assignment = True
    can_lock_journal = True
