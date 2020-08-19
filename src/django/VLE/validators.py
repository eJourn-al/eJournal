import json
import os
import re
from datetime import datetime

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, URLValidator
from sentry_sdk import capture_message

from VLE.models import Field, FileContext
from VLE.utils.error_handling import VLEMissingRequiredField


def validate_user_file(in_memory_uploaded_file, user):
    """Checks if size does not exceed 10MB. Or the user has reached his maximum storage space."""
    if in_memory_uploaded_file.size > settings.USER_MAX_FILE_SIZE_BYTES:
        raise ValidationError("Max size of file is {} Bytes".format(settings.USER_MAX_FILE_SIZE_BYTES))
    if len(in_memory_uploaded_file.name) > 128:  # reserving 37 for unique key, and the rest (91) as filepath
        raise ValidationError("Maximum filename length is 128, please rename the file.")

    user_files = user.filecontext_set.all()
    # Fast check for allowed user storage space
    if settings.USER_MAX_TOTAL_STORAGE_BYTES - len(user_files) * settings.USER_MAX_FILE_SIZE_BYTES <= \
       in_memory_uploaded_file.size:
        total_user_file_size = sum(user_file.file.size for user_file in user_files)
        if total_user_file_size > settings.USER_MAX_TOTAL_STORAGE_BYTES:
            if user.is_teacher:
                capture_message('Staff user {} file storage of {} exceeds desired limit'.format(
                    user.pk, total_user_file_size), level='error')
            else:
                raise ValidationError('Unsufficient storage space.')


def validate_email_files(files):
    """Checks if total size does not exceed 10MB."""
    if sum(file.size for file in files) > settings.USER_MAX_EMAIL_ATTACHMENT_BYTES:
        raise ValidationError(
            "Maximum email attachments size is {} Bytes.".format(settings.USER_MAX_EMAIL_ATTACHMENT_BYTES))


def validate_password(password):
    """Validates password by length, having a capital letter and a special character."""
    if len(password) < 8:
        raise ValidationError("Password needs to contain at least 8 characters.")
    if password == password.lower():
        raise ValidationError("Password needs to contain at least 1 capital letter.")
    if re.match(r'^[a-zA-Z0-9]+$', password):
        raise ValidationError("Password needs to contain a special character.")


def validate_entry_content(data, field):
    """Validates the given data based on its field type, any validation error will be thrown."""
    if field.required and not (data or data == ''):
        raise VLEMissingRequiredField(field)
    # QUESTION: Is '' really valid data for all fields?
    if not data:
        return

    if field.type == Field.RICH_TEXT:
        # TODO JIR: Check if any files are mentioned in the data, if so check if the FC and FC.file exist
        pass

    # TODO: improve VIDEO validator
    if field.type == Field.URL or field.type == Field.VIDEO:
        url_validate = URLValidator(schemes=Field.ALLOWED_URL_SCHEMES)
        url_validate(data)

    if field.type == Field.SELECTION:
        if data not in json.loads(field.options):
            raise ValidationError("Selected option is not in the given options.")

    if field.type == Field.DATE:
        try:
            datetime.strptime(data, Field.ALLOWED_DATE_FORMAT)
        except (ValueError, TypeError) as e:
            raise ValidationError(str(e))

    if field.type == Field.DATETIME:
        try:
            datetime.strptime(data, Field.ALLOWED_DATETIME_FORMAT)
        except (ValueError, TypeError) as e:
            raise ValidationError(str(e))

    if field.type == Field.FILE:
        try:
            int(data['id'])
        except (ValueError, KeyError):
            raise ValidationError("The data['id'] of a field file should contain the pk of the related file")

        # Ensures the FC still exists
        fc = FileContext.objects.get(pk=int(data['id']))
        if not os.path.isfile(fc.file.path):
            raise ValidationError("Entry references non existing file")

        if field.options:
            validator = FileExtensionValidator(field.options.split(', '))
            validator(fc.file)

    if field.type == Field.NO_SUBMISSION:
        raise ValidationError("No submission is allowed for this field.")
