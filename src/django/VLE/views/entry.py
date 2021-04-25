"""
entry.py.

In this file are all the entry api requests.
"""
from django.utils import timezone
from rest_framework import viewsets

import VLE.factory as factory
import VLE.serializers as serialize
import VLE.timeline as timeline
import VLE.utils.entry_utils as entry_utils
import VLE.utils.file_handling as file_handling
import VLE.utils.generic_utils as utils
import VLE.utils.responses as response
from VLE.models import Entry, Field, FileContext, Journal, Node, Template
from VLE.utils import grading


class EntryView(viewsets.ViewSet):
    """Entry view.

    This class creates the following api paths:
    POST /entries/ -- create a new entry
    PATCH /entries/<pk> -- partially update an entry
    """

    def create(self, request):
        """Create a new entry.

        Deletes remaining temporary user files if successful.

        Arguments:
        request -- the request that was send with
            journal_id -- the journal id
            template_id -- the template id to create the entry with
            node_id -- optional: the node to bind the entry to (only for entrydeadlines)
            content -- the list of {tag, data} tuples to bind data to a template field.
            category_ids -- list of category ids the entry should be associated with
        """
        journal_id, template_id, content_dict = utils.required_params(
            request.data, 'journal_id', 'template_id', 'content')
        node_id, category_ids, title = utils.optional_typed_params(
            request.data,
            (int, 'node_id'),
            (int, 'category_ids'),
            (str, 'title'),
        )

        journal = Journal.objects.get(pk=journal_id, authors__user=request.user)
        assignment = journal.assignment
        template = Template.objects.get(pk=template_id)

        request.user.check_permission('can_have_journal', assignment)

        if assignment.is_locked():
            return response.forbidden('The assignment is locked, entries can no longer be edited/changed.')

        if len(journal.needs_lti_link) > 0:
            return response.forbidden(journal.outdated_link_warning_msg)

        # Check if the template is available
        if not (node_id or assignment.format.template_set.filter(archived=False, preset_only=False,
                                                                 pk=template.pk).exists()):
            return response.forbidden('Entry template is not available.')

        if title and not template.chain.allow_custom_title:
            return response.forbidden('Entry does not allow for a custom title.')

        entry_utils.check_fields(template, content_dict)
        category_ids = Entry.validate_categories(category_ids, assignment, template)

        # Deadline entry
        if node_id:
            node = Node.objects.get(pk=node_id, journal=journal)
            entry_utils.validate_node(node, template)
        # Unlimited entry
        else:
            node = factory.make_node(journal)
        entry = factory.make_entry(template, request.user, node, category_ids, title)

        entry_utils.create_entry_content(content_dict, entry, request.user)
        # Notify teacher on new entry
        grading.task_journal_status_to_LMS.delay(journal.pk)

        return response.created({
            'added': entry_utils.get_node_index(journal, node, request.user),
            'nodes': timeline.get_nodes(journal, request.user),
            'entry': serialize.EntrySerializer(entry, context={'user': request.user}).data
        })

    def partial_update(self, request, *args, **kwargs):
        """Update an existing entry.

        Arguments:
        request -- request data
            data -- the new data for the course
        pk -- assignment ID

        Returns:
        On failure:
            unauthorized -- when the user is not logged in
            not found -- when the entry does not exist
            forbidden -- User not allowed to edit this entry
            unauthorized -- when the user is unauthorized to edit the entry
            bad_request -- when there is invalid data in the request
        On success:
            success -- with the new entry data
        """
        content_dict, = utils.required_params(request.data, 'content')
        title, = utils.optional_typed_params(request.data, (str, 'title'))
        entry_id, = utils.required_typed_params(kwargs, (int, 'pk'))
        entry = Entry.objects.get(pk=entry_id)
        journal = Journal.objects.get(node__entry=entry)
        assignment = journal.assignment

        if assignment.is_locked():
            return response.forbidden('The assignment is locked, entries can no longer be edited/changed.')
        request.user.check_permission('can_have_journal', assignment)
        if not (journal.authors.filter(user=request.user).exists() or request.user.is_superuser):
            return response.forbidden('You are not allowed to edit someone else\'s entry.')
        if entry.is_graded():
            return response.bad_request('You are not allowed to edit graded entries.')
        if entry.is_locked():
            return response.bad_request('You are not allowed to edit locked entries.')
        if len(journal.needs_lti_link) > 0:
            return response.forbidden(journal.outdated_link_warning_msg)
        if title and not entry.template.chain.allow_custom_title:
            return response.forbidden('Entry does not allow for a custom title.')

        # Check for required fields
        entry_utils.check_fields(entry.template, content_dict)

        # Attempt to edit the entries content.
        files_to_establish = []
        for (field_id, new_content) in content_dict.items():
            field = Field.objects.get(pk=field_id)
            if new_content is not None and field.type == field.FILE:
                new_content, = utils.required_typed_params(new_content, (str, 'id'))

            old_content = entry.content_set.filter(field=field)

            changed = False
            if old_content.exists():
                old_content = old_content.first()
                if not new_content:
                    old_content.data = None
                    old_content.save()
                    continue

                changed = old_content.data != new_content
                if changed:
                    old_content.data = new_content
                    old_content.save()
            # If there was no content in this field before, create new content with the new data.
            # This can happen with non-required fields, or when the given data is deleted.
            else:
                old_content = factory.make_content(entry, new_content, field)
                changed = True

            if changed:
                if field.type == field.FILE:
                    if field.required and not new_content:
                        raise FileContext.DoesNotExist
                    if new_content:
                        files_to_establish.append(
                            (FileContext.objects.get(pk=int(new_content)), old_content))

                # Establish all files in the rich text editor
                if field.type == Field.RICH_TEXT:
                    files_to_establish += [
                        (f, old_content) for f in file_handling.get_temp_files_from_rich_text(new_content)]

        for (fc, old_content) in files_to_establish:
            if fc.is_temp:
                file_handling.establish_file(request.user, file_context=fc, content=old_content,
                                             in_rich_text=old_content.field.type == Field.RICH_TEXT)

        grading.task_journal_status_to_LMS.delay(journal.pk)
        entry.last_edited_by = request.user
        entry.last_edited = timezone.now()
        entry.title = title
        entry.save()

        return response.success({'entry': serialize.EntrySerializer(entry, context={'user': request.user}).data})

    def destroy(self, request, *args, **kwargs):
        """Delete an entry and the node it belongs to.

        Arguments:
        request -- request data
        pk -- entry ID

        Returns:
        On failure:
            not found -- when the course does not exist
            unauthorized -- when the user is not logged in
            forbidden -- when the user is not in the course
        On success:
            success -- with a message that the course was deleted
        """
        pk, = utils.required_typed_params(kwargs, (int, 'pk'))

        entry = Entry.objects.get(pk=pk)
        journal = Journal.objects.get(node__entry=entry)
        assignment = journal.assignment

        if journal.authors.filter(user=request.user).exists():
            request.user.check_permission('can_have_journal', assignment, 'You are not allowed to delete entries.')
            if entry.is_graded():
                return response.forbidden('You are not allowed to delete graded entries.')
            if entry.is_locked():
                return response.forbidden('You are not allowed to delete locked entries.')
            if assignment.is_locked():
                return response.forbidden('You are not allowed to delete entries in a locked assignment.')
        elif not request.user.is_superuser:
            return response.forbidden('You are not allowed to delete someone else\'s entry.')
        if len(journal.needs_lti_link) > 0:
            return response.forbidden(journal.outdated_link_warning_msg)

        entry.delete()
        return response.success(description='Successfully deleted entry.')
