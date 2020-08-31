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
        self.add_course(test.factory.Course())


class AssignmentFactory(factory.django.DjangoModelFactory):
    """
    Defaults to a format consisting of two templates: Text and Colloquium

    It is ensured that the author is a teacher for each attached course. By default the author of the generated
    course is used.
    """
    class Meta:
        model = 'VLE.Assignment'

    class Params:
        group_assignment = factory.Trait(
            is_group_assignment=True,
            can_lock_journal=True
        )

    name = factory.Sequence(lambda x: "Assignment {}".format(x))
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

    format = factory.SubFactory('test.factory.format.FormatFactory', called_from_assignment=True)

    @factory.post_generation
    def courses(self, create, extracted, **kwargs):
        if not create:
            return

        _add_courses(self, create, extracted, **kwargs)

    @factory.post_generation
    def author(self, create, extracted, **kwargs):
        if not extracted and not kwargs:
            extracted = self.courses.first().author if self.courses.exists() else extracted
        test.factory.rel_factory(self, create, extracted, 'author', User, test.factory.Teacher, **kwargs)

    @factory.post_generation
    def make_author_teacher_in_all_courses(self, create, extracted, **kwargs):
        if not create or extracted is False:
            return

        for course in self.courses.all():
            if not Participation.objects.filter(course=course, user=self.author).exists():
                teacher_role = Role.objects.get(course=course, name='Teacher')
                test.factory.Participation(course=course, user=self.author, role=teacher_role)


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
