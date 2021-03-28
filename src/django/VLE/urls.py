"""
VLE URL Configuration.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')

Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')

Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))

"""
from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from VLE.lms_api import authenticate
from VLE.lti1p3 import launch
from VLE.views import common, email, user

urlpatterns = [
    url(r'^admin/', admin.site.urls),

    url(r'^', include(('VLE.views', 'VLE.views'), namespace='VLE')),

    path('token/', user.LoginView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),

    path('forgot_password/', email.forgot_password, name='forgot_password'),
    path('recover_password/', email.recover_password, name='recover_password'),
    path('verify_email/', email.verify_email, name='verify_email'),
    path('request_email_verification/', email.request_email_verification, name='request_email_verification'),
    path('send_feedback/', email.send_feedback, name='send_feedback'),

    # Launch from LMS, verifies jwt credentials and redirects to front end lti_launch point of entry
    path('lti/launch/', launch.launch, name='lti_launch'),
    path('lti/configure/', launch.launch_configuration, name='lti_launch_configuration'),
    url(r'^lti/login/$', launch.lti_login, name='lti_login'),
    url(r'^lms/authenticate/$', authenticate.lms_authenticate, name='lms_api_authenticate'),

    path('names/<int:course_id>/<int:assignment_id>/<int:journal_id>/', common.names, name='names'),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

if 'silk' in settings.INSTALLED_APPS:
    urlpatterns.append(url(r'^silk/', include('silk.urls', namespace='silk')))

if 'django_prometheus' in settings.INSTALLED_APPS:
    urlpatterns.append(url('', include('django_prometheus.urls')))
