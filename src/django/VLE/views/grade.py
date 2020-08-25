"""
grade.py.

In this file are all the grade api requests.
"""
from rest_framework import viewsets
from rest_framework.decorators import action

import VLE.factory as factory
import VLE.utils.generic_utils as utils
import VLE.utils.grading as grading
import VLE.utils.responses as response
from VLE.models import Assignment, Comment, Entry, Grade, Journal
from VLE.serializers import EntrySerializer, GradeHistorySerializer


class GradeView(viewsets.ViewSet):
    """Grade view.

    This class creates the following api paths:
    GET /grades/ -- gets the grade history of an entry
    POST /grades/ -- grade an entry
    """

    def list(self, request):
        """Get the grade history of an entry.

        Arguments:
        request -- request data
            entry_id -- entry ID

        Returns:
        On failure:
            unauthorized -- when the user is not logged in
            not found -- when the course does not exist
            forbidden -- when its not their own journal, or the user is not allowed to grade that journal
        On success:
            success -- with all historic grades corresponding to the entry
        """
        entry_id, = utils.required_typed_params(request.query_params, (int, "entry_id"))

        entry = Entry.objects.get(pk=entry_id)
        assignment = entry.node.journal.assignment

        request.user.check_permission('can_view_grade_history', assignment)

        grade_history = Grade.objects.filter(entry=entry)

        return response.success({'grade_history': GradeHistorySerializer(grade_history, many=True).data})

    def create(self, request):
        """Set a new grade for an entry.

        Arguments:
        request -- request data
            entry_id -- entry ID
            grade -- grade
            published -- published state

        Returns:
        On failure:
            unauthorized -- when the user is not logged in
            key_error -- missing keys
            not_found -- could not find the entry, author or assignment

        On success:
            success -- with the assignment data
        """
        entry_id, grade, published = utils.required_typed_params(request.data, (int, 'entry_id'), (float, 'grade'),
                                                                 (bool, 'published'))

        entry = Entry.objects.get(pk=entry_id)
        journal = entry.node.journal
        assignment = journal.assignment

        request.user.check_permission('can_grade', assignment)

        if published:
            request.user.check_permission('can_publish_grades', assignment)

        if grade is not None and grade < 0:
            return response.bad_request('Grade must be greater than or equal to zero.')

        grade = factory.make_grade(entry, request.user.pk, grade, published)

        if published:
            Comment.objects.filter(entry=entry).update(published=True)
        grading.task_journal_status_to_LMS.delay(journal.pk)

        return response.created({
            'entry': EntrySerializer(entry, context={'user': request.user}).data,
        })

    @action(methods=['patch'], detail=False)
    def publish_all_assignment_grades(self, request):
        """This will publish all (unpublished) grades for a given assignment."""
        assignment_id, = utils.required_typed_params(request.data, (int, 'assignment_id'))
        assignment = Assignment.objects.get(pk=assignment_id)

        request.user.check_permission('can_publish_grades', assignment)

        for journal in Journal.objects.filter(assignment=assignment).distinct():
            grading.publish_all_journal_grades(journal, request.user)
            grading.task_journal_status_to_LMS.delay(journal.pk)

        return response.success()
