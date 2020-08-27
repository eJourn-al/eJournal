"""
email.py.

In this file are all the email api requests.
This includes:
    /forgot_password/ -- to get the names belonging to the ids
"""
import VLE.utils.generic_utils as utils
import VLE.utils.responses as response
import VLE.validators as validators
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from VLE.models import User
from VLE.tasks import send_email_feedback, send_email_verification_link, send_password_recovery_link

from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.db.models import Q
from django.http import HttpResponse
from django.utils.html import escape


def index(request):
    return HttpResponse(escape(repr(request)))


@api_view(['POST'])
@permission_classes((AllowAny, ))
def forgot_password(request):
    """Handles a forgot password request.

    Arguments:
        identifier -- User claimed username / email.
        token -- Django stateless token, invalidated after password change or after a set time (by default three days).

    Generates a recovery token if a matching user can be found by either the prodived username or email.
    """
    identifier, = utils.required_params(request.data, 'identifier')

    # We are retrieving the username based on either the username or email
    user = User.objects.get(Q(email=identifier) | Q(username=identifier))
    if user.email == identifier:
        email = identifier
    else:
        email = 'your recovery address'

    if not user.email:
        return response.bad_request(
            description='The provided account has no known email address.')

    send_password_recovery_link.delay(user.pk)
    return response.success(
        description='An email was sent to {}, please check your inbox for further instructions.'.format(email))


@api_view(['POST'])
@permission_classes((AllowAny, ))
def recover_password(request):
    """Handles a reset password request.

    Arguments:
        username -- User claimed username.
        recovery_token -- Django stateless token, invalidated after password change or after a set time
            (by default three days).
        new_password -- The new user desired password.

    Updates password if the recovery_token is valid.
    """
    username, recovery_token, new_password = utils.required_params(
        request.data, 'username', 'recovery_token', 'new_password')

    user = User.objects.get(username=username)

    recovery_token, = utils.required_params(request.data, 'recovery_token')
    token_generator = PasswordResetTokenGenerator()
    if not token_generator.check_token(user, recovery_token):
        return response.bad_request('Invalid recovery token.')

    validators.validate_password(new_password)

    user.set_password(new_password)
    user.save()

    return response.success(description='Successfully changed the password, you can now log in.')


@api_view(['POST'])
@permission_classes((AllowAny, ))
def verify_email(request):
    """Handles an email verification request.

    Arguments:
        token -- User claimed email verification token.

    Updates the email verification status.
    """
    token, username = utils.required_params(request.data, 'token', 'username')
    user = User.objects.get(username=username)

    token_generator = PasswordResetTokenGenerator()
    if not token_generator.check_token(user, token):
        return response.bad_request(description='Invalid email verification token.')

    if user.verified_email:
        return response.success(description='Email address already verified.')

    user.verified_email = True
    user.save()
    return response.success(description='Successfully verified your email address.')


@api_view(['POST'])
def request_email_verification(request):
    """Request an email with a verifcation link for the user's email address."""
    if request.user.verified_email:
        return response.success(description='Email address already verified.')

    email, = utils.optional_params(request.data, 'email')

    if not email and not request.user.email:
        return response.bad_request(description='Please provide an email address.')

    if email and request.user.email != email:
        request.user.email = email
        request.user.verified_email = False
        request.user.save()

    send_email_verification_link.delay(request.user.pk)
    return response.success(
        description='An email was sent to {}, please check your inbox for further \
                     instructions.'.format(request.user.email))


@api_view(['POST'])
def send_feedback(request):
    """Send an email with feedback to the developers.

    Arguments:
    request -- the request that was sent.
        topic -- the topic of the feedback.
        type -- the type of feedback.
        feedback -- the actual feedback.
        browser -- the browser of the user who sends the feedback.
        files -- potential files as attachments, currently only one file is processed.

    Returns:
    On failure:
        bad request -- when required keys are missing or file sizes too big.
        unauthorized -- when the user is not logged in.
    On success:
        success -- with a description.
    """
    request.user.check_verified_email()
    topic, ftype, feedback, user_agent, url = \
        utils.required_params(request.data, 'topic', 'ftype', 'feedback', 'user_agent', 'url')

    if request.FILES:
        files = request.FILES.getlist('files')
        validators.validate_email_files(files)
        if request.user.feedback_file:
            request.user.feedback_file.delete()
        request.user.feedback_file = files[0]
        request.user.save()
        send_email_feedback.delay(
            request.user.pk, topic, ftype, feedback, user_agent, url, file_content_type=files[0].content_type)
    else:
        send_email_feedback.delay(request.user.pk, topic, ftype, feedback, user_agent, url)

    return response.success(description='Thank you for contacting support, we\'ll get back to you as soon as possible!')
