import json
import os
import re
from datetime import datetime

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, URLValidator
from sentry_sdk import capture_message

import VLE.models
import VLE.utils.error_handling
import VLE.utils.file_handling as file_handling


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


def validate_youtube_url_with_video_id(url):
    r = r"^((?:https?:)?\/\/)?((?:www|m)\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(watch\?v=|embed/|v/|.+\?v=)?(?P<id>[A-Za-z0-9=_-]{11})" # NOQA E501
    if not (isinstance(url, str) and re.match(r, url)):
        raise ValidationError('Enter a valid YouTube video URL.')


def validate_kaltura_video_embed_code(data):
    r = r"(?:<iframe.*src=\")(?P<src>https:\/\/api\.eu\.kaltura\.com[^ ]*)(?:\")"
    if not (isinstance(data, str) and re.match(r, data)):
        raise ValidationError('Enter a valid Kaltura embed code.')


def validate_video_data(field, data):
    if field.youtube_allowed and field.kaltura_allowed:
        try:
            validate_kaltura_video_embed_code(data)
        except ValidationError:
            validate_youtube_url_with_video_id(data)
    elif field.youtube_allowed:
        validate_youtube_url_with_video_id(data)
    elif field.kaltura_allowed:
        validate_kaltura_video_embed_code(data)


def validate_entry_content(content, field): # NOQA C901
    """Validates the given data based on its field type, any validation error will be thrown."""
    if field.required and not (content or content == ''):
        raise VLE.utils.error_handling.VLEMissingRequiredField(field)
    if not content:
        return

    if field.type == VLE.models.Field.RICH_TEXT:
        for access_id in file_handling.get_access_ids_from_rich_text(content):
            fc = VLE.models.FileContext.objects.filter(access_id=access_id)
            if not fc.exists():
                raise ValidationError('Rich text contains reference to non existing file.')
            fc = fc.first()
            if not fc.file or not os.path.exists(fc.file.path):
                raise ValidationError('Rich text linked to file context whose file does not exists.')

    if field.type == VLE.models.Field.URL:
        url_validate = URLValidator(schemes=VLE.models.Field.ALLOWED_URL_SCHEMES)
        url_validate(content)

    if field.type == VLE.models.Field.VIDEO:
        validate_video_data(field, content)

    if field.type == VLE.models.Field.SELECTION:
        if content not in json.loads(field.options):
            raise ValidationError('Selected option is not in the given options.')

    if field.type == VLE.models.Field.DATE:
        try:
            datetime.strptime(content, settings.ALLOWED_DATE_FORMAT)
        except (ValueError, TypeError) as e:
            raise ValidationError(str(e))

    if field.type == VLE.models.Field.DATETIME:
        try:
            datetime.strptime(content, settings.ALLOWED_DATETIME_FORMAT)
        except (ValueError, TypeError) as e:
            raise ValidationError(str(e))

    if field.type == VLE.models.Field.FILE:
        try:
            int(content['id'])
        except (ValueError, KeyError, TypeError):
            raise ValidationError('The content of a field file should follow {field.pk: FileContext.pk}')

        # Ensures the FC still exists
        fc = VLE.models.FileContext.objects.get(pk=int(content['id']))
        if not os.path.isfile(fc.file.path):
            raise ValidationError('Entry references non existing file.')

        if field.options:
            validator = FileExtensionValidator(field.options.split(', '))
            validator(fc.file)

    if field.type == VLE.models.Field.NO_SUBMISSION:
        raise ValidationError('No submission is allowed for this field.')
