import datetime
import test.factory

import factory
from django.utils import timezone

from VLE.models import AssignmentParticipation, Participation, Role, User


def _add_courses(self, create, extracted, **kwargs):
    if extracted or extracted == []:
        for course in extracted:
            self.courses.add(course)
    else:
        if self.active_lti_id:
            course_factory = test.factory.LtiCourse
        else:
            course_factory = test.factory.Course
        if self.author:
            self.courses.add(course_factory(**{**kwargs, 'author': self.author}))
        else:
            self.courses.add(course_factory(**kwargs))


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
        default = self.courses.first().author if self.courses.exists() else None
        test.factory.rel_factory(self, create, extracted, 'author', User, test.factory.Teacher,
                                 default=default, **kwargs)

    @factory.post_generation
    def make_author_teacher_in_all_courses(self, create, extracted, **kwargs):
        if not create or extracted is False:
            return

        for course in self.courses.all():
            if not Participation.objects.filter(course=course, user=self.author).exists():
                teacher_role = Role.objects.get(course=course, name='Teacher')
                test.factory.Participation(course=course, user=self.author, role=teacher_role)

    @factory.post_generation
    def create_assignment_participations_for_all_courses_users(self, create, extracted, **kwargs):
        if not create or extracted is False:
            return

        existing = AssignmentParticipation.objects.filter(assignment=self).values('user')
        for user in User.objects.filter(pk__in=self.courses.values('users')).exclude(pk__in=existing):
            AssignmentParticipation.objects.create(assignment=self, user=user)


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
