"""
entry.py.

In this file are all the entry api requests.
"""
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
        """
        journal_id, template_id, content_list = utils.required_params(
            request.data, "journal_id", "template_id", "content")
        node_id, = utils.optional_params(request.data, "node_id")

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

        entry_utils.check_fields(template, content_list)

        # Node specific entry
        if node_id:
            node = Node.objects.get(pk=node_id, journal=journal)
            entry = entry_utils.add_entry_to_node(node, template, request.user)
        # Template specific entry
        else:
            node = factory.make_node(journal)
            entry = factory.make_entry(template, request.user, node)

        try:
            files_to_establish = []
            for content in content_list:
                field_id, = utils.required_typed_params(content, (int, 'id'))
                field = Field.objects.get(pk=field_id)
                data, = utils.required_params(content, 'data')
                if data is not None and field.type == field.FILE:
                    data, = utils.required_typed_params(data, (str, 'id'))

                created_content = factory.make_content(node.entry, data, field)

                if field.type == field.FILE:
                    if field.required and not data:
                        raise FileContext.DoesNotExist
                    if data:
                        files_to_establish.append(
                            (FileContext.objects.get(pk=int(data)), created_content))

                # Establish all files in the rich text editor
                if field.type == Field.RICH_TEXT:
                    files_to_establish += [(f, created_content) for f in file_handling.get_files_from_rich_text(data)]

        # If anything fails during creation of the entry, delete the entry
        except Exception as e:
            node.entry.delete()
            # If there is a newly created node, delete that as well
            if not node_id:
                node.delete()

            # If it is a file issue, raise with propper response, else respond with the exception that was raised
            if type(e) == FileContext.DoesNotExist:
                return response.bad_request('One of your files was not correctly uploaded, please try again.')
            else:
                raise e

        for (file, content) in files_to_establish:
            file_handling.establish_file(
                request.user, file.access_id, content=content, in_rich_text=content.field.type == Field.RICH_TEXT)

        # Notify teacher on new entry
        grading.task_journal_status_to_LMS.delay(journal.pk)

        # Delete old user files
        file_handling.remove_unused_user_files(request.user)

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
        content_list, = utils.required_params(request.data, 'content')
        entry_id, = utils.required_typed_params(kwargs, (int, 'pk'))
        entry = Entry.objects.get(pk=entry_id)
        journal = entry.node.journal
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

        # Check for required fields
        entry_utils.check_fields(entry.template, content_list)

        # Attempt to edit the entries content.
        files_to_establish = []
        for content in content_list:
            field_id, = utils.required_typed_params(content, (int, 'id'))
            data, = utils.required_params(content, 'data')
            field = Field.objects.get(pk=field_id)
            if data is not None and field.type == field.FILE:
                data, = utils.required_typed_params(data, (str, 'id'))

            old_content = entry.content_set.filter(field=field)
            changed = False
            if old_content.exists():
                old_content = old_content.first()
                if old_content.field.pk != field_id:
                    return response.bad_request('The given content does not match the accompanying field type.')
                if not data:
                    old_content.data = None
                    old_content.save()
                    continue

                changed = old_content.data != data
                if changed:
                    entry_utils.patch_entry_content(request.user, entry, old_content, field, data, assignment)
            # If there was no content in this field before, create new content with the new data.
            # This can happen with non-required fields, or when the given data is deleted.
            else:
                old_content = factory.make_content(entry, data, field)
                changed = True

            if changed:
                if field.type == field.FILE:
                    if field.required and not data:
                        raise FileContext.DoesNotExist
                    if data:
                        files_to_establish.append(
                            (FileContext.objects.get(pk=int(data)), old_content))

                # Establish all files in the rich text editor
                if field.type == Field.RICH_TEXT:
                    files_to_establish += [(f, old_content) for f in file_handling.get_files_from_rich_text(data)]

        for (file, content) in files_to_establish:
            file_handling.establish_file(
                request.user, file.access_id, content=content, in_rich_text=content.field.type == Field.RICH_TEXT)

        file_handling.remove_unused_user_files(request.user)
        grading.task_journal_status_to_LMS.delay(journal.pk)
        entry.last_edited_by = request.user
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
        journal = entry.node.journal
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

        if entry.node.type != Node.ENTRYDEADLINE:
            entry.node.delete()
        entry.delete()
        return response.success(description='Successfully deleted entry.')
