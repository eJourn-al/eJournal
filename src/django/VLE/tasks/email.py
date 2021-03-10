from __future__ import absolute_import, unicode_literals

from celery import shared_task
from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

import VLE.models

# QUESTION: What action should be taken if sending the email goes wrong? E.g. SMTP auth exception
# Idempotent tasks and retry? Will still require handling for when the retries ultimately fail


@shared_task
def send_push_notification(notification_pk):
    """Send a notification with corresponding pk to the user.

    Note: does not send the notification if it is not already sent.
    """
    notification = VLE.models.Notification.objects.get(pk=notification_pk)
    if notification.sent:
        return {
            'description': 'Notification nr {} was already sent'.format(notification_pk),
            'successful': False,
        }
    if not notification.user.verified_email:
        return {
            'description': 'Notification nr {} has unverified email adress'.format(notification_pk),
            'successful': False,
        }

    email_data = {
        'heading': notification.title,
        'main_content': notification.content,
        'button_text': notification.button_text,
        'full_name': notification.user.full_name,
        'button_url': notification.url,
        'profile_url': '{}/Profile'.format(settings.BASELINK)
    }

    html_content = render_to_string('call_to_action.html', {'email_data': email_data})
    text_content = strip_tags(html_content)
    if notification.assignment:
        context = '{}, {}'.format(notification.assignment.name, notification.course.name)
    else:
        context = notification.course.name

    email = EmailMultiAlternatives(
        subject='{} in {} - eJournal'.format(notification.title, context),
        body=text_content,
        from_email=settings.EMAILS.support.sender,
        headers={'Content-Type': 'text/plain'},
        to=[notification.user.email]
    )

    email.attach_alternative(html_content, 'text/html')
    email.send()
    notification.sent = True
    notification.save()

    return {
        'description': 'Sent notification nr {}'.format(notification_pk),
        'successful': True,
    }


@shared_task
def send_email_verification_link(user_pk):
    """Sends an email verification link to the users email adress."""
    user = VLE.models.User.objects.get(pk=user_pk)

    email_data = {}
    email_data['heading'] = 'Email verification'
    token_generator = PasswordResetTokenGenerator()
    token = token_generator.make_token(user)
    email_data['main_content'] = """\
    We have received a request for email verification. If it was you who made this request, \
    please click the button below to verify your email address. If you have not made this \
    request please ignore this email."""
    email_data['full_name'] = user.full_name
    email_data['extra_content'] = 'Token: {}'.format(token)
    email_data['button_url'] = '{}/EmailVerification/{}/{}'.format(settings.BASELINK, user.username, token)
    email_data['button_text'] = 'Verify Email'
    email_data['profile_url'] = '{}/Profile'.format(settings.BASELINK)

    html_content = render_to_string('call_to_action.html', {'email_data': email_data})
    text_content = strip_tags(html_content)

    email = EmailMultiAlternatives(
        subject='eJournal email verification',
        body=text_content,
        from_email=settings.EMAILS.noreply.sender,
        headers={'Content-Type': 'text/plain'},
        to=[user.email]
    )

    email.attach_alternative(html_content, 'text/html')
    email.send()


@shared_task
def send_invite_emails(user_pks):
    """Sends an invite link to join the platform to the users email adress."""
    users = VLE.models.User.objects.filter(pk__in=user_pks)
    instance_name = VLE.models.Instance.objects.get(pk=1).name
    token_generator = PasswordResetTokenGenerator()
    for user in users:
        email_data = {}
        email_data['heading'] = 'Welcome to eJournal!'
        token = token_generator.make_token(user)
        email_data['main_content'] = """
        You have been invited to eJournal by {}. Please click the button below to activate your account.""" \
            .format(instance_name)
        email_data['full_name'] = user.full_name
        email_data['extra_content'] = 'Username: {}'.format(user.username)
        email_data['button_url'] = '{}/SetPassword/{}/{}?new_user=true'.format(settings.BASELINK, user.username, token)
        email_data['button_text'] = 'Activate account'
        email_data['profile_url'] = '{}/Profile'.format(settings.BASELINK)

        html_content = render_to_string('call_to_action.html', {'email_data': email_data})
        text_content = strip_tags(html_content)

        email = EmailMultiAlternatives(
            subject='Complete your registration for eJournal at {}'.format(instance_name),
            body=text_content,
            from_email=settings.EMAILS.noreply.sender,
            headers={'Content-Type': 'text/plain'},
            to=[user.email]
        )

        email.attach_alternative(html_content, 'text/html')
        email.send()


@shared_task
def send_password_recovery_link(user_pk):
    user = VLE.models.User.objects.get(pk=user_pk)

    email_data = {}
    email_data['heading'] = 'Password recovery'
    token_generator = PasswordResetTokenGenerator()
    token = token_generator.make_token(user)
    email_data['main_content'] = """\
    We have received a request for password recovery. If it was you who made this request, \
    please click the button below to set a new password. If you have not made this \
    request please ignore this email."""
    email_data['full_name'] = user.full_name
    email_data['extra_content'] = 'Token: {}'.format(token)
    email_data['button_url'] = '{}/SetPassword/{}/{}'.format(settings.BASELINK, user.username, token)
    email_data['button_text'] = 'Set New Password'
    email_data['profile_url'] = '{}/Profile'.format(settings.BASELINK)

    html_content = render_to_string('call_to_action.html', {'email_data': email_data})
    text_content = strip_tags(html_content)

    email = EmailMultiAlternatives(
        subject='eJournal password recovery',
        body=text_content,
        from_email=settings.EMAILS.noreply.sender,
        headers={'Content-Type': 'text/plain'},
        to=[user.email]
    )

    email.attach_alternative(html_content, 'text/html')
    email.send()


@shared_task
def send_email_feedback(user_pk, topic, ftype, feedback, user_agent, url, file_content_type=None):
    """Sends the feedback of an user to the developers."""
    user = VLE.models.User.objects.get(pk=user_pk)

    f_body = 'TYPE: {}\n\n'.format(ftype)
    f_body += 'FEEDBACK BY: {}\n'.format(user.username)
    f_body += 'EMAIL: {}\n'.format(user.email)
    f_body += 'TEACHER: {}\n'.format(user.is_teacher)
    f_body += 'ROLES: {}\n'.format(VLE.models.Role.objects.filter(role__user=user).values('name'))
    f_body += 'USER-AGENT: {}\n'.format(user_agent)
    f_body += 'URL: {}\n\n'.format(url)
    f_body += 'THE FEEDBACK:\n{}'.format(feedback)

    r_email_data = {}
    r_email_data['feedback'] = feedback
    r_email_data['ftype'] = ftype
    r_email_data['profile_url'] = '{}/Profile'.format(settings.BASELINK)

    r_html_content = render_to_string('feedback.html', {'email_data': r_email_data})
    r_text_content = strip_tags(r_html_content)

    attachments = []
    if user.feedback_file:
        r_email_data['attachments_added'] = True
        attachments.append((user.feedback_file.name, user.feedback_file.read(), file_content_type))

    reply = EmailMultiAlternatives(
        subject='Re: {}'.format(topic),
        body=r_text_content,
        attachments=attachments,
        from_email=settings.EMAILS.support.sender,
        headers={'Content-Type': 'text/plain'},
        to=[user.email],
        bcc=[settings.EMAILS.support.email],
    )

    forward = EmailMultiAlternatives(
        subject='Additional support info: {}'.format(topic),
        body=f_body,
        attachments=attachments,
        from_email=settings.EMAILS.support.sender,
        to=[settings.EMAILS.support.email],
        headers={'Content-Type': 'text/plain'}
    )

    reply.attach_alternative(r_html_content, 'text/html')
    reply.send()
    forward.send()

    if user.feedback_file:
        user.feedback_file.delete()
