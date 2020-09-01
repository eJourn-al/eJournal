from test.factory.user import DEFAULT_PASSWORD

import factory

from django.conf import settings


class JWTParamsFactory(factory.Factory):
    class Meta:
        model = dict

    user_id = factory.Sequence(lambda x: 'LMS_user_id{}'.format(x))
    custom_user_full_name = 'full name of LMS user'
    custom_user_email = factory.Sequence(lambda x: 'valid_LMS_email{}@address.com'.format(x))
    custom_user_image = 'https://LMS.com/user_profile_image_link.png'
    custom_username = factory.Sequence(lambda x: 'LMS_username{}'.format(x))


class JWTTestUserParamsFactory(JWTParamsFactory):
    custom_user_email = ''
    user_id = factory.Sequence(lambda x: "305c9b180a9ce9684ea62aeff2b2e97052cf2d4b{}".format(x))
    custom_user_full_name = settings.LTI_TEST_STUDENT_FULL_NAME
    custom_username = factory.Sequence(lambda x: '305c9b180a9ce9684ea62aeff2b2e97052cf2d4c1{}'.format(x))


class UserParamsFactory(factory.Factory):
    class Meta:
        model = dict

    username = factory.Sequence(lambda x: 'user{}'.format(x))
    password = DEFAULT_PASSWORD
