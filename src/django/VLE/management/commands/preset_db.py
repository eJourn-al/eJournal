"""
Generate preset data.

Generate preset data and save it to the database.
"""

import datetime
import random

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand
from faker import Faker

import VLE.factory as factory
from VLE.models import Assignment, AssignmentParticipation, Course, Field, FileContext, Journal, Node, Template, User
from VLE.utils import file_handling

faker = Faker()


class Command(BaseCommand):
    """Generate preset data and save it to the database."""

    help = 'Generates useful data for the database.'

    def gen_users(self):
        """Generate users with password 'pass'."""
        users_examples = {
            "Student": {
                "username": "student",
                "full_name": "Lars van Hijfte",
                "verified_email": True,
                "password": "pass",
                "email": "lars@eJournal.app",
                "is_superuser": False,
                "is_teacher": False
            },
            "Student2": {
                "username": "student2",
                "full_name": "Rick Watertor",
                "verified_email": True,
                "password": "pass",
                "email": "rick@eJournal.app",
                "is_superuser": False,
                "is_teacher": False
            },
            "Student3": {
                "username": "student3",
                "full_name": "Dennis Wind",
                "password": "pass",
                "email": "dennis@eJournal.app",
                "verified_email": True,
                "is_superuser": False,
                "is_teacher": False
            },
            "Student4": {
                "username": "student4",
                "full_name": "Maarten van Keulen",
                "password": "pass",
                "email": "maarten@eJournal.app",
                "verified_email": False,
                "is_superuser": False,
                "is_teacher": False
            },
            "Student5": {
                "username": "student5",
                "full_name": "Zi Long Zhu",
                "password": "pass",
                "email": "zi@eJournal.app",
                "verified_email": False,
                "is_superuser": False,
                "is_teacher": False
            },
            "TestUser": {
                "username": "305c9b180a9ce9684ea62aeff2b2e97052cf2d4b1",
                "full_name": settings.LTI_TEST_STUDENT_FULL_NAME,
                "password": "pass",
                "email": "",
                "verified_email": False,
                "is_superuser": False,
                "is_teacher": False,
                "is_test_student": True,
            },
            "Teacher": {
                "username": "teacher",
                "full_name": "Engel Hamer",
                "password": "pass",
                "email": "test@eJournal.app",
                "verified_email": True,
                "is_superuser": False,
                "is_teacher": True
            },
            "TA": {
                "username": "TA",
                "full_name": "De TA van TAing",
                "verified_email": False,
                "password": "pass",
                "email": "ta@eJournal.app",
                "is_superuser": False,
                "is_teacher": False
            },
            "TA2": {
                "username": "TA2",
                "full_name": "Backup TA van TAing",
                "verified_email": False,
                "password": "pass",
                "email": "ta2@eJournal.app",
                "is_superuser": False,
                "is_teacher": False
            },
            "Superuser": {
                "username": "superuser",
                "full_name": "Super User",
                "password": "pass",
                "email": "superuser@eJournal.app",
                "verified_email": False,
                "is_superuser": True,
                "is_teacher": True,
                "is_staff": True
            }
        }

        self.users = {}

        for key, value in users_examples.items():
            self.users[key] = User.objects.create(**value)
            self.users[key].set_password(value['password'])
            self.users[key].profile_picture = settings.DEFAULT_PROFILE_PICTURE
            self.users[key].save()

    def gen_courses(self):
        """Generate courses."""
        courses_examples = {
            "Portfolio Academische Vaardigheden - Cohort 1": {
                "pk": 1697,
                "name": "Portfolio Academische Vaardigheden - Cohort 1",
                "abbr": "PAV1",
                "author": self.users["Teacher"],
                "students": [self.users[s] for s in ["Student", "Student2", "Student3", "Student4", "Student5",
                                                     "TestUser"]],
                "teachers": [self.users["Teacher"]],
                "tas": [self.users["TA"]],
                "start_date": faker.date("2018-09-01"),
                "end_date": faker.date("2021-07-31"),
                "student_group_names": ["Cobol", "Smalltalk"]
            },
            "Portfolio Academische Vaardigheden - Cohort 2": {
                "pk": 1698,
                "name": "Portfolio Academische Vaardigheden - Cohort 2",
                "abbr": "PAV2",
                "author": self.users["Teacher"],
                "students": [self.users[s] for s in ["Student", "Student2", "Student3", "Student4", "Student5",
                                                     "TestUser"]],
                "teachers": [self.users["Teacher"]],
                "tas": [self.users["TA2"]],
                "start_date": faker.date("2019-09-01"),
                "end_date": faker.date("2022-07-31"),
                "student_group_names": ["Algol", "Ruby"]
            }
        }

        self.courses = {}
        for c in courses_examples.values():
            course = Course(pk=c["pk"], name=c["name"], abbreviation=c["abbr"], startdate=c["start_date"],
                            enddate=c["end_date"], author=c["author"])
            course.save()

            student_groups = [factory.make_course_group(g, course) for g in c["student_group_names"]]
            staff_group = factory.make_course_group("Staff", course)

            role_student = factory.make_role_student('Student', course)
            role_ta = factory.make_role_ta('TA', course)
            role_teacher = factory.make_role_teacher('Teacher', course)

            for student in c["students"]:
                factory.make_participation(
                    student, course, role_student, [random.choice(student_groups)], notify_user=False)
            for ta in c["tas"]:
                factory.make_participation(ta, course, role_ta, [random.choice(student_groups)], notify_user=False)
            for teacher in c["teachers"]:
                factory.make_participation(teacher, course, role_teacher, [staff_group], notify_user=False)

            self.courses[c["name"]] = course

    def gen_templates(self, format):
        """Generate templates.

        One with title, summary, experience, requested points and proof.
        One with only text.
        """
        template_examples = [
            {
                "name": "Colloquium",
                "fields": [
                    {"title": "Title", "location": 0, "type": Field.TEXT},
                    {"title": "Summary", "location": 1, "type": Field.RICH_TEXT},
                    {"title": "Experience", "location": 2, "type": Field.RICH_TEXT},
                    {"title": "Requested Points", "location": 3, "type": Field.TEXT},
                    {"title": "Proof", "location": 4, "type": Field.FILE, "required": False},
                ]
            },
            {
                "name": "Mentorgesprek",
                "fields": [
                    {"title": "Text", "location": 0, "type": Field.TEXT},
                ]
            },
            {
                "name": "Files",
                "fields": [
                    {
                        "title": "IMG",
                        "location": 0,
                        "type": Field.FILE,
                        "required": False,
                        "options": 'bmp, gif, ico, cur, jpg, jpeg, jfif, pjpeg, pjp, png, svg',
                    },
                    {
                        "title": "FILE",
                        "location": 1,
                        "type": Field.FILE,
                        "required": False,
                    },
                    {
                        "title": "PDF",
                        "location": 2,
                        "type": Field.FILE,
                        "required": False,
                        "options": 'pdf',
                    },
                ]
            }
        ]

        templates = []
        for t in template_examples:
            template = factory.make_entry_template(t["name"], format)
            templates.append(template)
            for f in t["fields"]:
                factory.make_field(
                    template, f["title"], f["location"], f["type"],
                    required=f.get('required', True), options=f.get('options', None)
                )

        return templates

    def gen_format(self):
        """Generate a format."""
        format_examples = [
            {
                "presets": [
                    {"type": Node.PROGRESS, "points": 10},
                ]
            },
            {
                "presets": [
                    {"type": Node.PROGRESS, "points": 5},
                    {"type": Node.PROGRESS, "points": 1, "description": "1 day", "deadline_days": 1},
                    {"type": Node.PROGRESS, "points": 3, "description": "1 week", "deadline_days": 7},
                    {"type": Node.ENTRYDEADLINE, "template": 1, "description": "1 week entrydl", "deadline_days": 7},
                    {"type": Node.ENTRYDEADLINE, "template": 1},
                ]
            },
            {
                "templates": [0, 1],
                "presets": [
                    {"type": Node.PROGRESS, "points": 10},
                ]
            },
        ]

        self.formats = []
        for f in format_examples:
            format = factory.make_default_format()
            templates = self.gen_templates(format)

            for p in f["presets"]:
                if "deadline_days" in p:
                    due_date = datetime.datetime.utcnow() + datetime.timedelta(days=p["deadline_days"])
                else:
                    due_date = faker.date_time_between(start_date="now", end_date="+1y", tzinfo=None)

                if p["type"] == Node.PROGRESS:
                    node = factory.make_progress_node(format, due_date, p["points"])
                    if "description" in p:
                        node.description = p["description"]
                        node.save()
                elif p["type"] == Node.ENTRYDEADLINE:
                    factory.make_entrydeadline_node(format, due_date, templates[p["template"]])

            self.formats.append(format)

    def gen_assignments(self):
        """Generate assignments."""
        assign_examples = [
            {
                "name": "Logboek",
                "description": "<p>This is a logboek for all your logging purposes</p>",
                "courses": [
                    self.courses["Portfolio Academische Vaardigheden - Cohort 1"],
                    self.courses["Portfolio Academische Vaardigheden - Cohort 2"]
                ],
                "format": 0,
                "author": self.users["Teacher"],
                "is_group_assignment": False,
            },
            {
                "name": "Colloquium",
                "description": "<p>This is the best colloquium logbook in the world</p>",
                "courses": [self.courses["Portfolio Academische Vaardigheden - Cohort 1"]],
                "format": 1,
                "author": self.users["Teacher"],
                "is_group_assignment": False,
            },
            {
                "name": "Group Assignment",
                "description":
                    "<p>This is a group assignment. This is purely for testing group assignment stuff.<br/>" +
                    "Initialized with student and student2 in 1 journal and student3 in another.</p>",
                "courses": [self.courses["Portfolio Academische Vaardigheden - Cohort 2"]],
                "format": 2,
                "author": self.users["Teacher"],
                "is_group_assignment": True,
            }
        ]

        self.assignments = []
        for a in assign_examples:
            format = self.formats[a["format"]]
            faker.date_time_between(start_date="now", end_date="+1y", tzinfo=None)
            assignment = factory.make_assignment(a["name"], a["description"], a["author"], format, courses=a["courses"],
                                                 is_published=True, is_group_assignment=a["is_group_assignment"])
            self.assignments.append(assignment)

        journal = factory.make_journal(self.assignments[2], author_limit=3)
        journal.add_author(AssignmentParticipation.objects.get(assignment=assignment, user=self.users["Student2"]))
        journal.add_author(AssignmentParticipation.objects.get(assignment=assignment, user=self.users["Student"]))
        journal.save()
        journal = factory.make_journal(self.assignments[2], author_limit=3)
        journal.add_author(AssignmentParticipation.objects.get(assignment=assignment, user=self.users["Student3"]))

    def gen_journals(self):
        """Generate journals."""
        self.journals = Journal.objects.all()

    def gen_entries(self, assignment):
        """Generate entries."""
        coll = Template.objects.get(name='Colloquium', format__assignment=assignment)
        mentor = Template.objects.get(name='Mentorgesprek', format__assignment=assignment)
        files = Template.objects.get(name='Files', format__assignment=assignment)
        entries_to_gen = [
            {
                'user': self.users['Student'],
                'entries': [
                    {
                        'template': coll,
                        'grade': 3,
                        'published': True,
                        'amount': 3
                    },
                    {
                        'template': mentor,
                        'grade': 1,
                        'published': False,
                        'amount': 5
                    },
                    {
                        'template': coll,
                        'grade': None,
                        'published': False,
                        'amount': 3
                    },
                    {
                        'template': files,
                        'grade': None,
                        'published': False,
                        'amount': 1
                    },
                ]
            },
            {
                'user': self.users['Student2'],
                'entries': [
                    {
                        'template': mentor,
                        'grade': 2,
                        'published': True,
                        'amount': 3
                    },
                    {
                        'template': coll,
                        'grade': 2,
                        'published': False,
                        'amount': 0
                    },
                    {
                        'template': coll,
                        'grade': None,
                        'published': False,
                        'amount': 10
                    },
                ]
            },
            {
                'user': self.users['Student3'],
                'entries': [
                    {
                        'template': coll,
                        'grade': 2,
                        'published': True,
                        'amount': 2
                    },
                    {
                        'template': mentor,
                        'grade': 1,
                        'published': False,
                        'amount': 3
                    },
                    {
                        'template': mentor,
                        'grade': None,
                        'published': False,
                        'amount': 0
                    },
                ]
            },
            {
                'user': self.users['Student4'],
                'entries': [
                    {
                        'template': mentor,
                        'grade': 2,
                        'published': True,
                        'amount': 4
                    },
                    {
                        'template': coll,
                        'grade': 2,
                        'published': False,
                        'amount': 0
                    },
                    {
                        'template': mentor,
                        'grade': None,
                        'published': False,
                        'amount': 0
                    },
                ]
            },
        ]
        for user_entries in entries_to_gen:
            user = user_entries['user']
            for entry_obj in user_entries['entries']:
                for _ in range(entry_obj['amount']):
                    node = factory.make_node(Journal.objects.get(authors__user=user, assignment=assignment))
                    entry = factory.make_entry(entry_obj['template'], user, node)
                    if entry_obj['grade'] is not None:
                        factory.make_grade(entry, self.users['Teacher'].pk, entry_obj['grade'], entry_obj['published'])

    def gen_content(self):
        """Generate content for an entry."""
        for journal in self.journals:
            for node in journal.node_set.all():
                if node.type == Node.ENTRY or node.type == Node.ENTRYDEADLINE:
                    if node.entry is None:
                        continue

                    template = node.entry.template
                    for field in template.field_set.all():
                        if field.type in [Field.TEXT, Field.RICH_TEXT]:  # Files requires the actual file...
                            if "Requested Points" in field.title:
                                factory.make_content(node.entry, str(random.randint(1, 3)), field)
                            else:
                                factory.make_content(node.entry, faker.catch_phrase(), field)

                        try:
                            if field.type == Field.FILE and (not field.options or 'png' in field.options):
                                with open('../vue/public/journal-view.png', 'rb') as file:
                                    image = SimpleUploadedFile('test-image.png', file.read(), content_type='image/png')
                                    fc = FileContext.objects.create(
                                        file=image, author=journal.authors.first().user, file_name=image.name)
                                    content = factory.make_content(node.entry, str(fc.pk), field)
                                    file_handling.establish_file(journal.authors.first().user, fc.pk, content=content)
                            elif field.type == Field.FILE:
                                with open('./VLE/management/commands/dummy.pdf', 'rb') as file:
                                    pdf = SimpleUploadedFile(
                                        'dummy.pdf', file.read(), content_type='application/pdf')
                                    fc = FileContext.objects.create(
                                        file=pdf, author=journal.authors.first().user, file_name=pdf.name)
                                    content = factory.make_content(node.entry, str(fc.pk), field)
                                    file_handling.establish_file(journal.authors.first().user, fc.pk, content=content)
                        except FileNotFoundError:
                            continue

    def handle(self, *args, **options):
        """Generate data to test and fill the database with.

        This only contains the 'useful data'. For random data, execute demo_db as well.
        """
        self.gen_users()
        self.gen_courses()
        self.gen_format()
        self.gen_assignments()
        self.gen_journals()
        self.gen_entries(Assignment.objects.get(name='Logboek'))
        self.gen_entries(Assignment.objects.get(name='Colloquium'))
        self.gen_content()
