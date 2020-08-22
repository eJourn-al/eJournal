"""
assignment.py.

In this file are all the assignment api requests.
"""
import csv

import chardet
from dateutil.relativedelta import relativedelta
from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action

import VLE.factory as factory
import VLE.utils.generic_utils as utils
import VLE.utils.responses as response
import VLE.validators as validators
from VLE.models import Assignment, Course, Field, Journal, PresetNode, Template, User
from VLE.serializers import AssignmentSerializer, CourseSerializer, SmallAssignmentSerializer, TemplateSerializer
from VLE.utils import file_handling, grading
from VLE.utils.error_handling import VLEMissingRequiredKey, VLEParamWrongType


def day_neutral_datetime_increment(date, months=0):
    return date + relativedelta(months=months, weekday=date.weekday())


def set_assignment_dates(assignment, months=0):
    """Add an offset of [months] months to the assignment dates."""
    if assignment.unlock_date:
        assignment.unlock_date = day_neutral_datetime_increment(assignment.unlock_date, months)
    if assignment.due_date:
        assignment.due_date = day_neutral_datetime_increment(assignment.due_date, months)
    if assignment.lock_date:
        assignment.lock_date = day_neutral_datetime_increment(assignment.lock_date, months)


class AssignmentView(viewsets.ViewSet):
    """Assignment view.

    This class creates the following api paths:
    GET /assignments/ -- gets all the assignments
    POST /assignments/ -- create a new assignment
    GET /assignments/<pk> -- gets a specific assignment
    PATCH /assignments/<pk> -- partially update an assignment
    DEL /assignments/<pk> -- delete an assignment
    GET /assignments/upcoming/ -- get the upcoming assignments of the logged in user
    """

    def list(self, request):
        """Get the assignments from a course for the user.

        Arguments:
        request -- request data
            course_id -- course ID

        Returns:
        On failure:
            unauthorized -- when the user is not logged in
            not found -- when the course does not exist
            forbidden -- when the user is not part of the course
        On success:
            success -- with the assignment data

        """
        try:
            course_id, = utils.required_typed_params(request.query_params, (int, 'course_id'))
            course = Course.objects.get(pk=course_id)
            request.user.check_participation(course)
            courses = [course]
        except (VLEMissingRequiredKey, VLEParamWrongType):
            course = None
            courses = request.user.participations.all()

        query = Assignment.objects.filter(courses__in=courses).distinct()
        viewable = [assignment for assignment in query if request.user.can_view(assignment)]
        serializer = SmallAssignmentSerializer(viewable, many=True, context={'user': request.user, 'course': course})

        data = serializer.data
        for i, assignment in enumerate(data):
            data[i]['lti_couples'] = len(Assignment.objects.get(id=assignment['id']).lti_id_set)
        return response.success({'assignments': data})

    def create(self, request):
        """Create a new assignment.

        Arguments:
        request -- request data
            name -- name of the assignment
            description -- description of the assignment
            course_id -- id of the course the assignment belongs to
            points_possible -- the possible amount of points for the assignment
            unlock_date -- (optional) date the assignment becomes available on
            due_date -- (optional) date the assignment is due for
            lock_date -- (optional) date the assignment becomes unavailable on
            lti_id -- (optional) id labeled link to LTI instance

        Returns:
        On failure:
            unauthorized -- when the user is not logged in
            not_found -- could not find the course with the given id
            key_error -- missing keys
            forbidden -- the user is not allowed to create assignments in this course

        On success:
            success -- with the assignment data

        """
        name, description, course_id = utils.required_typed_params(
            request.data, (str, 'name'), (str, 'description'), (int, 'course_id'))
        unlock_date, due_date, lock_date, lti_id, is_published, points_possible, is_group_assignment, \
            can_set_journal_name, can_set_journal_image, can_lock_journal, remove_grade_upon_leaving_group = \
            utils.optional_typed_params(
                request.data, (str, 'unlock_date'), (str, 'due_date'), (str, 'lock_date'), (str, 'lti_id'),
                (bool, 'is_published'), (float, 'points_possible'), (bool, 'is_group_assignment'),
                (bool, 'can_set_journal_name'), (bool, 'can_set_journal_image'), (bool, 'can_lock_journal'),
                (bool, 'remove_grade_upon_leaving_group'))
        course = Course.objects.get(pk=course_id)

        request.user.check_permission('can_add_assignment', course)

        assignment = factory.make_assignment(
            name, description, courses=[course], author=request.user, active_lti_id=lti_id,
            points_possible=points_possible, unlock_date=unlock_date, due_date=due_date,
            lock_date=lock_date, is_published=is_published, is_group_assignment=is_group_assignment or False,
            can_set_journal_name=can_set_journal_name or False, can_set_journal_image=can_set_journal_image or False,
            can_lock_journal=can_lock_journal or False,
            remove_grade_upon_leaving_group=remove_grade_upon_leaving_group or False)

        # Add new lti id to assignment
        if lti_id is not None:
            request.user.check_permission('can_add_assignment', course)
            assignment.add_lti_id(lti_id, course)
            request.data.pop('lti_id')

        file_handling.establish_rich_text(request.user, assignment.description, assignment=assignment)
        file_handling.remove_unused_user_files(request.user)
        serializer = AssignmentSerializer(
            assignment,
            context={'user': request.user, 'course': course,
                     'journals': request.user.has_permission('can_grade', assignment)}
        )
        return response.created({'assignment': serializer.data})

    def retrieve(self, request, pk=None):
        """Retrieve an assignment.

        Arguments:
        request -- request data
            lti -- if this is set, the pk is an lti_id, not a 'normal' id
            course_id -- get information about that course
        pk -- assignment ID

        Returns:
        On failure:
            unauthorized -- when the user is not logged in
            not_found -- could not find the course with the given id
            forbidden -- not allowed to retrieve assignments in this course

        On success:
            success -- with the assignment data

        """
        if 'lti' in request.query_params:
            assignment = Assignment.objects.get(lti_id_set__contains=[pk])
        else:
            assignment = Assignment.objects.get(pk=pk)

        try:
            course_id, = utils.required_typed_params(request.query_params, (int, 'course_id'))
            course = Course.objects.get(id=course_id)
        except (VLEMissingRequiredKey, VLEParamWrongType):
            course = None

        request.user.check_can_view(assignment)

        serializer = AssignmentSerializer(
            assignment,
            context={'user': request.user, 'course': course,
                     'journals': request.user.has_permission('can_grade', assignment)}
        )
        return response.success({'assignment': serializer.data})

    def partial_update(self, request, *args, **kwargs):
        """Update an existing assignment.

        Arguments:
        request -- request data
            data -- the new data for the assignment
        pk -- assignment ID

        Returns:
        On failure:
            unauthorized -- when the user is not logged in
            not found -- when the assignment does not exist
            forbidden -- User not allowed to edit this assignment
            unauthorized -- when the user is unauthorized to edit the assignment
            bad_request -- when there is invalid data in the request
        On success:
            success -- with the new assignment data

        """
        pk, = utils.required_typed_params(kwargs, (int, 'pk'))
        assignment = Assignment.objects.get(pk=pk)
        course = None

        request.user.check_permission('can_edit_assignment', assignment)

        # Remove data that must not be changed by the serializer
        req_data = request.data
        if not (request.user.is_superuser or request.user == assignment.author):
            req_data.pop('author', None)

        is_published, can_set_journal_name, can_set_journal_image, can_lock_journal = \
            utils.optional_typed_params(
                request.data, (bool, 'is_published'),
                (bool, 'can_set_journal_name'), (bool, 'can_set_journal_image'), (bool, 'can_lock_journal'))

        # Set active lti course
        active_lti_course, = utils.optional_typed_params(request.data, (int, 'active_lti_course'))
        if active_lti_course is not None:
            assignment.set_active_lti_course(Course.objects.get(pk=active_lti_course))
            request.data.pop('active_lti_course')

        # Add new lti id to assignment
        lti_id, = utils.optional_typed_params(request.data, (str, 'lti_id'))
        if lti_id is not None:
            course_id, = utils.required_typed_params(request.data, (int, 'course_id'))
            course = Course.objects.get(pk=course_id)
            request.user.check_permission('can_add_assignment', course)
            assignment.add_lti_id(lti_id, course)
            request.data.pop('lti_id')

        # Update the other data
        serializer = AssignmentSerializer(
            assignment, data=req_data, context={'user': request.user, 'course': course}, partial=True)
        if not serializer.is_valid():
            return response.bad_request()
        serializer.save()

        return response.success({'assignment': serializer.data})

    def destroy(self, request, *args, **kwargs):
        """Delete an existing assignment from a course.

        Arguments:
        request -- request data
            course_id -- the course ID of course this assignment belongs to
        pk -- assignment ID

        Returns:
        On failure:
            unauthorized -- when the user is not logged in
            not found -- when the assignment or course does not exist
            unauthorized -- when the user is not logged in
            forbidden -- when the user cannot delete the assignment
        On success:
            success -- with a message that the course was deleted

        """
        assignment_id, = utils.required_typed_params(kwargs, (int, 'pk'))
        course_id, = utils.required_typed_params(request.query_params, (int, 'course_id'))
        assignment = Assignment.objects.get(pk=assignment_id)
        course = Course.objects.get(pk=course_id)

        request.user.check_permission('can_delete_assignment', course)

        intersecting_assignment_lti_id = assignment.get_lti_id_from_course(course)
        if intersecting_assignment_lti_id:
            if assignment.active_lti_id == intersecting_assignment_lti_id and len(assignment.lti_id_set) > 1:
                return response.bad_request('This assignment cannot be removed from this course, since it is' +
                                            ' currently configured for grade passback to the LMS')
            course.assignment_lti_id_set.remove(intersecting_assignment_lti_id)
            assignment.lti_id_set.remove(intersecting_assignment_lti_id)
            course.save()

        assignment.courses.remove(course)
        assignment.save()

        if assignment.active_lti_id is not None and assignment.active_lti_id in course.assignment_lti_id_set:
            course.assignment_lti_id_set.remove(assignment.active_lti_id)
            course.save()

        # If the assignment is only connected to one course, delete it completely
        if assignment.courses.count() == 0:
            assignment.delete()
            return response.success(description='Successfully deleted the assignment.')
        else:
            return response.success(description='Successfully removed the assignment from {}.'.format(str(course)))

    @action(methods=['get'], detail=False)
    def upcoming(self, request):
        """Get upcoming deadlines for the requested user.

        Arguments:
        request -- request data
            course_id -- course ID

        Returns:
        On failure:
            unauthorized -- when the user is not logged in
            not found -- when the course does not exist
        On success:
            success -- upcoming assignments

        """
        try:
            course_id, = utils.required_typed_params(request.query_params, (int, 'course_id'))
            course = Course.objects.get(pk=course_id)
            request.user.check_participation(course)
            courses = [course]
        except (VLEMissingRequiredKey, VLEParamWrongType):
            course = None
            courses = request.user.participations.all()

        now = timezone.now()
        query = Assignment.objects.filter(
            Q(lock_date__gt=now) | Q(lock_date=None), courses__in=courses
        ).distinct()
        viewable = [assignment for assignment in query if request.user.can_view(assignment)]
        upcoming = SmallAssignmentSerializer(
            viewable, context={'user': request.user, 'course': course}, many=True).data

        return response.success({'upcoming': upcoming})

    @action(methods=['post'], detail=True)
    def add_bonus_points(self, request, *args, **kwargs):
        """Give students bonus points though file submission.

        This will scan over the included file, and give all the users the bonus points supplied.
        Format:
        [username1], [bonus_points1]
        [username2], [bonus_points2]

        NOTE: Also possible to use semicolon instead of comma.

        Arguments:
        request
            file -- list of all the bonus points
        pk -- assignment ID
        """
        assignment_id, = utils.required_typed_params(kwargs, (int, 'pk'))
        assignment = Assignment.objects.get(pk=assignment_id)

        request.user.check_permission('can_grade', assignment)

        if not (request.FILES and 'file' in request.FILES):
            return response.bad_request('No accompanying file found in the request.')

        validators.validate_user_file(request.FILES['file'], request.user)

        bonuses = dict()
        incorrect_format_lines = dict()
        unknown_users = dict()
        duplicates = dict()
        non_participants = dict()

        # Guess which encoding is used.
        encoding = chardet.detect(request.FILES['file'].read())['encoding']
        try:
            # Go back to first line of the file, then read and decode lines.
            csv_file = request.FILES['file'].open().read().decode(encoding)
        except (TypeError, UnicodeDecodeError):
            return response.bad_request({'general': 'Not a valid csv file.'})
        # Initialize csv reader to parse file.
        try:
            dialect = csv.Sniffer().sniff(csv_file, delimiters=';')
            csv_reader = csv.reader(csv_file.splitlines(), dialect)
        except Exception:
            csv_reader = csv.reader(csv_file.splitlines())

        for line_nr, row in enumerate(csv_reader, 1):
            try:
                # Ignore empty lines.
                if len(row) == 0:
                    continue

                username, bonus = row
                bonus = float(bonus)
                user = User.objects.get(username=str(username))
                journal = Journal.objects.get(assignment=assignment, authors__user=user)
                if journal in bonuses:
                    duplicates[line_nr] = username
                else:
                    bonuses[journal] = bonus
            except ValueError:
                incorrect_format_lines[line_nr] = ','.join(row)
            except User.DoesNotExist:
                unknown_users[line_nr] = username
            except Journal.DoesNotExist:
                non_participants[line_nr] = username

        if unknown_users or incorrect_format_lines or duplicates or non_participants:
            errors = dict()

            if incorrect_format_lines:
                errors['incorrect_format_lines'] = incorrect_format_lines
            if duplicates:
                errors['duplicates'] = duplicates
            if unknown_users:
                errors['unknown_users'] = unknown_users
            if non_participants:
                errors['non_participants'] = non_participants

            return response.bad_request(errors)

        for j, b in bonuses.items():
            j.bonus_points = b
            j.save()
            grading.task_journal_status_to_LMS.delay(j.pk)

        return response.success()

    @action(methods=['get'], detail=False)
    def importable(self, request):
        """Get all assignments that a user can import a format from.

        Returns a list of tuples consisting of courses and importable assignments."""
        courses = Course.objects.filter(participation__user=request.user.id,
                                        participation__role__can_edit_assignment=True)

        importable = []
        for course in courses:
            assignments = Assignment.objects.filter(courses=course)
            if assignments:
                importable.append({
                    'course': CourseSerializer(course).data,
                    'assignments': SmallAssignmentSerializer(
                        assignments, context={'user': request.user}, many=True).data
                })
        return response.success({'data': importable})

    @action(methods=['post'], detail=True)
    def copytemplate(self, request, pk):
        """Import a template.

        Arguments:
        request -- request data
            template_id -- template to import
        pk -- assignment to import to
        """
        assignment = Assignment.objects.get(pk=pk)
        request.user.check_permission('can_edit_assignment', assignment)

        template_id, = utils.required_typed_params(request.data, (int, 'template_id'))
        template = Template.objects.get(pk=template_id)
        request.user.check_permission('can_edit_assignment', template.format.assignment)

        source_template_id = template.pk
        template.pk = None
        template.format = assignment.format
        template.save()

        for field in Field.objects.filter(template=source_template_id):
            field.pk = None
            field.template = template
            field.save()

        template_data = TemplateSerializer(template, context={'user': request.user}).data
        template_data.pop('id')
        template_data.pop('archived')
        template_data.pop('format')
        template.delete()

        for field in template_data['field_set']:
            field.pop('id')
            field.pop('template')

        return response.success({'template': template_data})

    @action(methods=['post'], detail=True)
    def copy(self, request, pk):
        """Import an assignment format.
        Users should have edit rights for the assignment import source.

        Arguments:
        request -- request data
            course_id -- course id which will receive the assignment import
            months_offset -- number of months to shift all dates
            years_offset -- number of years to shift all dates
        pk -- assignment import source ID

        """
        course_id, months_offset = utils.required_typed_params(request.data, (int, 'course_id'), (int, 'months_offset'))
        course = Course.objects.get(pk=course_id)
        assignment_source = Assignment.objects.get(pk=pk)

        request.user.check_permission('can_add_assignment', course)
        request.user.check_permission('can_edit_assignment', assignment_source)

        source_format_id = assignment_source.format.pk

        format = assignment_source.format
        format.pk = None
        format.save()

        assignment = assignment_source
        assignment.is_published = False
        assignment.pk = None
        set_assignment_dates(assignment, months_offset)

        # One to one fields needs to be updated before save else we would have a duplicate key
        assignment.format = format
        assignment.save()

        # Many to many field requires manual update, only set the course we are importing into
        assignment.courses.set([])
        assignment.add_course(course)
        assignment.save()

        template_dict = {}

        for template in Template.objects.filter(format=source_format_id, archived=False):
            source_template_id = template.pk
            template.pk = None
            template.format = format
            template.save()
            template_dict[source_template_id] = template.pk

            for field in Field.objects.filter(template=source_template_id):
                field.pk = None
                field.template = template
                field.save()

        journals = assignment.journal_set.all()
        for preset in PresetNode.objects.filter(format=source_format_id):
            preset.pk = None
            preset.format = format
            preset.due_date = day_neutral_datetime_increment(preset.due_date, months_offset)
            if preset.unlock_date:
                preset.unlock_date = day_neutral_datetime_increment(preset.unlock_date, months_offset)
            if preset.lock_date:
                preset.lock_date = day_neutral_datetime_increment(preset.lock_date, months_offset)
            if preset.forced_template:
                preset.forced_template = Template.objects.get(pk=template_dict[preset.forced_template.pk])
            preset.save()
            for journal in journals:
                factory.make_node(journal, None, preset.type, preset)

        # Add new lti id to new assignment
        lti_id, = utils.optional_typed_params(request.data, (str, 'lti_id'))
        if lti_id is not None:
            assignment.add_lti_id(lti_id, course)
            request.data.pop('lti_id')

        # Update author also
        assignment.author = request.user
        assignment.save()

        return response.success({'assignment_id': assignment.pk})

    @action(methods=['get'], detail=True)
    def participants_without_journal(self, request, pk):
        """Get all assignment participants that are not yet a member of a journal.

        Returns a list of users."""
        assignment = Assignment.objects.get(pk=pk)

        request.user.check_permission('can_manage_journals', assignment)

        participants_without_journal = []
        for participant_without_journal in User.objects.filter(assignmentparticipation__assignment__pk=pk,
                                                               assignmentparticipation__journal=None):
            if participant_without_journal.has_permission('can_have_journal', assignment):
                participants_without_journal.append({
                    'full_name': participant_without_journal.full_name,
                    'id': participant_without_journal.pk
                })

        return response.success({'participants': participants_without_journal})
