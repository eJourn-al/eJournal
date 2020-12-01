"""
Generate preset data.

Generate preset data and save it to the database.
"""
import random
import test.factory as factory

from dateutil.relativedelta import relativedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from faker import Faker

from VLE.models import Course, Field, Journal, Role, User

faker = Faker()


class Command(BaseCommand):
    help = 'Setup a new isolated course with a specifiable number of students.'

    def gen_users(self, n_students):
        self.teacher = User.objects.filter(username='teacher').first()
        if not self.teacher:
            self.teacher = factory.Teacher(
                username='teacher',
                password='pass',
                email='test@eJournal.app',
            )

        self.tas = User.objects.filter(username__startswith='TA')
        if not self.tas.exists():
            self.tas = [
                factory.Student(
                    username='TA',
                    verified_email=False,
                    password='pass',
                    email='ta@eJournal.app',
                ),
                factory.Student(
                    username='TA2',
                    verified_email=False,
                    password='pass',
                    email='ta2@eJournal.app',
                )
            ]

        student_count = User.objects.filter(username__startswith='user').count()
        self.students = [factory.Student(password='pass', __sequence=student_count + i) for i in range(n_students)]

    def gen_course(self):
        course_name = 'Performance Course'
        course_number = Course.objects.filter(name__contains=course_name).count()

        self.course = factory.Course(
            name=f'{course_name} {course_number}',
            abbreviation=f'SPEED{course_number}',
            author=self.teacher,
            startdate=faker.date('2019-09-01'),
            enddate=faker.date('2022-07-31'),
        )

        student_groups = [factory.Group(course=self.course, name=name, lti_id=None) for name in ['Speedy', 'Gonzales']]
        staff_group = factory.Group(name='Staff', course=self.course)

        role_student = Role.objects.get(name='Student', course=self.course)
        role_ta = Role.objects.get(name='TA', course=self.course)

        for student in self.students:
            factory.Participation(
                user=student, course=self.course, role=role_student, group=random.choice(student_groups))
        for ta in self.tas:
            factory.Participation(user=ta, course=self.course, role=role_ta, group=random.choice(student_groups))
        teacher_p = self.course.author.participation_set.get(course=self.course)
        teacher_p.groups.add(staff_group)

    def gen_assignment(self, n_students):
        self.assignment = factory.Assignment(
            name='Performance Assignment',
            description=f'''
                <p>Used for performance testing, holds familiar teacher and tas as expected roles + {n_students}
                students</p>
            ''',
            courses=[self.course],
            format__templates=[{'type': Field.RICH_TEXT}],
            due_date=timezone.now() + relativedelta(years=1, days=1),
            lock_date=timezone.now() + relativedelta(years=1, days=2),
        )

        factory.ProgressPresetNode(format=self.assignment.format, target=10)

    def gen_entries(self):
        for j in Journal.objects.filter(assignment=self.assignment):
            entry = factory.UnlimitedEntry(node__journal=j, gen_content__from_file=True)
            random.choice([factory.Grade(grade=random.randint(0, 3), entry=entry), None])

    def add_arguments(self, parser):
        parser.add_argument('n_students', type=int, nargs='?', default=100)

    def handle(self, *args, **options):
        self.gen_users(options['n_students'])
        self.gen_course()
        self.gen_assignment(options['n_students'])
        self.gen_entries()
