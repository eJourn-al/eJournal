
ADMIN_INST = [
    'http://purl.imsglobal.org/vocab/lis/v2/institution/person#Administrator',
    'urn:lti:instrole:ims/lis/Administrator',
    'urn:lti:sysrole:ims/lis/SysAdmin',
]
ADMIN = [
    'http://purl.imsglobal.org/vocab/lis/v2/membership#Administrator',
]

TEACHER = [
    'http://purl.imsglobal.org/vocab/lis/v2/membership#Instructor',
    'urn:lti:instrole:ims/lis/Instructor',
    'urn:lti:role:ims/lis/Instructor',
] + ADMIN_INST + ADMIN

STUDENT = [
    'http://purl.imsglobal.org/vocab/lis/v2/membership#Learner',
    'urn:lti:sysrole:ims/lis/User',
]
TA = [
    'http://purl.imsglobal.org/vocab/lis/v2/membership/Instructor#TeachingAssistant',
]


def to_ejournal_role_name(roles):
    if not roles:
        return 'Student'
    if any(role in TEACHER for role in roles):
        return 'Teacher'
    elif any(role in TA for role in roles):
        return 'TA'
    return 'Student'
