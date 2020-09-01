
ADMIN_INST = "http://purl.imsglobal.org/vocab/lis/v2/institution/person#Administrator"
ADMIN = "http://purl.imsglobal.org/vocab/lis/v2/membership#Administrator"
TEACHER = "http://purl.imsglobal.org/vocab/lis/v2/membership#Instructor"
STUDENT = "http://purl.imsglobal.org/vocab/lis/v2/membership#Learner"
TA = "http://purl.imsglobal.org/vocab/lis/v2/membership/Instructor#TeachingAssistant"


def to_ejournal_role(roles):
    if TEACHER in roles:
        return 'Teacher'
    elif TA in roles:
        return 'TA'
    return 'Student'
