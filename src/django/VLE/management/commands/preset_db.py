"""
Generate preset data.

Generate preset data and save it to the database.
"""
import random
import test.factory as factory

from dateutil.relativedelta import relativedelta
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone
from faker import Faker

from VLE.models import Entry, Journal, Node, Role, User

faker = Faker()


class Command(BaseCommand):
    """Generate preset data and save it to the database."""

    help = 'Generates useful data for the database.'

    def gen_users(self):
        self.student = factory.Student(
            username='student',
            full_name='Lars van Hijfte',
            password='pass',
            email='lars@eJournal.app',
            verified_email=False,
        )
        self.student2 = factory.Student(
            username='student2',
            full_name='Rick Watertor',
            password='pass',
            email='rick@eJournal.app',
            verified_email=False,
        )
        self.student3 = factory.Student(
            username='student3',
            full_name='Dennis Wind',
            password='pass',
            email='dennis@eJournal.app',
            verified_email=False,
        )
        self.student4 = factory.Student(
            username='student4',
            full_name='Maarten van Keulen',
            password='pass',
            email='maarten@eJournal.app',
            verified_email=False,
        )
        self.student5 = factory.Student(
            username='student5',
            full_name='Zi Long Zhu',
            password='pass',
            email='zi@eJournal.app',
            verified_email=False,
        )
        self.test_user = factory.TestUser(is_test_student=True)
        self.teacher = factory.Teacher(
            username='teacher',
            full_name='Engel Hamer',
            password='pass',
            email='test@eJournal.app',
            verified_email=False,
        )
        self.ta = factory.Student(
            username='TA',
            full_name='De TA van TAing',
            password='pass',
            email='ta@eJournal.app',
            verified_email=False,
        )
        self.ta2 = factory.Student(
            username='TA2',
            full_name='Backup TA van TAing',
            password='pass',
            email='ta2@eJournal.app',
            verified_email=False,
        )
        self.superuser = factory.Admin(
            username='superuser',
            full_name='Super User',
            password='pass',
            email='superuser@eJournal.app',
            verified_email=False,
            is_superuser=True,
            is_teacher=True,
            is_staff=True
        )

        self.students = [self.student, self.student2, self.student3, self.student4, self.student5]
        self.tas = [self.ta, self.ta2]
        self.users = self.students + self.tas + [self.teacher] + [self.test_user] + [self.superuser]

    def gen_courses(self):
        self.courses = {
            'Portfolio Academische Vaardigheden - Cohort 1': {
                'instance': factory.Course(
                    pk=1697,
                    name='Portfolio Academische Vaardigheden - Cohort 1',
                    abbreviation='PAV1',
                    author=self.teacher,
                    startdate=faker.date('2018-09-01'),
                    enddate=faker.date('2021-07-31'),
                ),
                'students': self.students + [self.test_user],
                'student_group_names': ['Cobol', 'Smalltalk'],
                'tas': [self.ta],
            },
            'Portfolio Academische Vaardigheden - Cohort 2':  {
                'instance': factory.Course(
                    pk=1698,
                    name='Portfolio Academische Vaardigheden - Cohort 2',
                    abbreviation='PAV2',
                    author=self.teacher,
                    startdate=faker.date('2019-09-01'),
                    enddate=faker.date('2022-07-31'),
                ),
                'students': self.students + [self.test_user],
                'tas': [self.ta2],
                'student_group_names': ['Algol', 'Ruby']
            },
        }

        for c in self.courses.values():
            course = c['instance']
            student_groups = [
                factory.Group(course=course, name=name, lti_id=None) for name in c['student_group_names']]
            staff_group = factory.Group(name='Staff', course=course)

            role_student = Role.objects.get(name='Student', course=course)
            role_ta = Role.objects.get(name='TA', course=course)

            for student in c['students']:
                factory.Participation(
                    user=student, course=course, role=role_student, group=random.choice(student_groups))
            for ta in c['tas']:
                factory.Participation(user=ta, course=course, role=role_ta, group=random.choice(student_groups))
            teacher_p = course.author.participation_set.get(course=course)
            teacher_p.groups.add(staff_group)

    def gen_assignments(self):
        self.logboek = factory.Assignment(
            name='Logboek',
            description='<p>This is a logboek for all your logging purposes</p>',
            courses=[
                self.courses['Portfolio Academische Vaardigheden - Cohort 1']['instance'],
                self.courses['Portfolio Academische Vaardigheden - Cohort 2']['instance']
            ],
            format__templates=False,
            due_date=timezone.now() + relativedelta(years=1, days=1),
            lock_date=timezone.now() + relativedelta(years=1, days=2),
        )
        self.colloquium = factory.Assignment(
            name='Colloquium',
            description='<p>This is the best colloquium logbook in the world</p>',
            courses=[self.courses['Portfolio Academische Vaardigheden - Cohort 1']['instance']],
            format__templates=False,
            due_date=timezone.now() + relativedelta(years=1, days=1),
            lock_date=timezone.now() + relativedelta(years=1, days=2),
        )
        self.group_assignment = factory.Assignment(
            name='Group Assignment',
            description='<p>This is a group assignment. This is purely for testing group assignment stuff.<br/>' +
                        'Initialized with student and student2 in 1 journal and student3 in another.</p>',
            courses=[self.courses['Portfolio Academische Vaardigheden - Cohort 2']['instance']],
            is_group_assignment=True,
            format__templates=False,
            due_date=timezone.now() + relativedelta(years=1, days=1),
            lock_date=timezone.now() + relativedelta(years=1, days=2),
        )

        self.assignments = [self.logboek, self.colloquium, self.group_assignment]

    def gen_group_journals(self):
        """
        Creating an assignment will create an AP for ALL of its linked course users.
        Journals are created upon the creation of an AP except if we are dealing with a group assignment.
        """
        factory.GroupJournal(
            assignment=self.group_assignment,
            ap=False,
            add_users=[self.student, self.student2, self.student3],
            entries__n=0,
        )
        factory.GroupJournal(
            assignment=self.group_assignment,
            ap=False,
            add_users=[self.student4, self.student5],
            entries__n=0,
        )

    def gen_format(self):
        for a in self.assignments:
            factory.FilesTemplate(format=a.format)
            factory.ColloquiumTemplate(format=a.format)
            factory.MentorgesprekTemplate(format=a.format)

        # Logboek
        factory.ProgressPresetNode(
            format=self.logboek.format,
            target=10,
            due_date=timezone.now() + relativedelta(years=1),
            lock_date=timezone.now() + relativedelta(years=1),
        )

        # Colloquium
        factory.ProgressPresetNode(
            format=self.colloquium.format,
            target=1,
            due_date=timezone.now() + relativedelta(days=1),
            lock_date=timezone.now() + relativedelta(days=1),
            description='One day',
        )
        factory.ProgressPresetNode(
            format=self.colloquium.format,
            target=3,
            due_date=timezone.now() + relativedelta(weeks=7),
            lock_date=timezone.now() + relativedelta(weeks=7),
            description='One week',
        )
        factory.ProgressPresetNode(
            format=self.colloquium.format,
            target=5,
            due_date=timezone.now() + relativedelta(years=1),
        )
        factory.DeadlinePresetNode(
            format=self.colloquium.format,
            due_date=timezone.now() + relativedelta(weeks=7),
            lock_date=timezone.now() + relativedelta(weeks=7),
            forced_template=self.colloquium.format.template_set.get(name='Mentorgesprek')
        )
        factory.DeadlinePresetNode(
            format=self.colloquium.format,
            due_date=timezone.now() + relativedelta(months=7),
            lock_date=timezone.now() + relativedelta(months=7),
            forced_template=self.colloquium.format.template_set.get(name='Mentorgesprek')
        )

        # Group Assignment
        factory.ProgressPresetNode(format=self.group_assignment.format, target=10)

    def gen_entries(self):
        for a in self.assignments:
            # NOTE: carefull to use a.journal_set or query via AP, both will yield teacher journals
            for j in Journal.objects.filter(assignment=a):
                entry = factory.UnlimitedEntry(node__journal=j, gen_content__from_file=True)
                random.choice([factory.Grade(grade=random.randint(0, 3), entry=entry), None])

                # Colloquium holds some preset nodes
                if a.name == 'Colloquium':
                    deadline_nodes = list(j.node_set.filter(type=Node.ENTRYDEADLINE))
                    n_deadline_entries = random.randint(0, j.node_set.filter(type=Node.ENTRYDEADLINE).count())
                    for deadline_node in random.sample(deadline_nodes, n_deadline_entries):
                        factory.PresetEntry(
                            node__preset=deadline_node.preset, node__journal=j, gen_content__from_file=True)

    def gen_journal_import_requests(self):
        """
        Generates a JIR for each logboek student (who is also a colloquium student) from colloquium into logboek
        Generates one JIR from group assignment to logboek for 'Student'
        """
        for logboek_ap in self.logboek.assignmentparticipation_set.filter(user__in=self.students):
            col_ap = self.colloquium.assignmentparticipation_set.filter(user=logboek_ap.user)
            if col_ap.exists():
                col_ap = col_ap.first()
                if Entry.objects.filter(node__journal=col_ap.journal).exists():
                    factory.JournalImportRequest(
                        source=col_ap.journal, target=logboek_ap.journal, author=logboek_ap.user)

        student_logboek = self.logboek.journal_set.get(authors__user=self.student)
        student_group_journal = self.group_assignment.journal_set.get(authors__user=self.student)
        factory.JournalImportRequest(source=student_group_journal, target=student_logboek, author=self.student)

    def add_arguments(self, parser):
        parser.add_argument('n_performance_students', type=int, nargs='?', default=0)

    def handle(self, *args, **options):
        """
        Generates a dummy data for a testing environment.
        """
        self.gen_users()
        self.gen_courses()
        self.gen_assignments()
        self.gen_group_journals()
        self.gen_format()
        self.gen_entries()
        self.gen_journal_import_requests()
        User.objects.filter(pk__in=[
            self.student.pk, self.student2.pk, self.student3.pk, self.ta2.pk
        ]).update(verified_email=True)

        if options['n_performance_students']:
            call_command('add_performance_course', options['n_performance_students'])
