import factory


class RoleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'VLE.Role'

    name = factory.Sequence(lambda x: 'Undefined role ' + str(x))
    course = factory.SubFactory('test.factory.course.CourseFactory')


class StudentRoleFactory(RoleFactory):
    name = 'Student'
    course = factory.SubFactory('test.factory.course.CourseFactory', student_role=factory.SelfAttribute('..'))

    can_have_journal = True
    can_comment = True


class TaRoleFactory(RoleFactory):
    name = 'TA'
    course = factory.SubFactory('test.factory.course.CourseFactory', ta_role=factory.SelfAttribute('..'))

    can_comment = True
    can_view_course_users = True
    can_edit_course_user_group = True
    can_view_all_journals = True
    can_grade = True
    can_publish_grades = True
    can_view_unpublished_assignment = True


class TeacherRoleFactory(TaRoleFactory):
    name = 'Teacher'
    course = factory.SubFactory('test.factory.course.CourseFactory', teacher_role=factory.SelfAttribute('..'))

    can_edit_course_details = True
    can_delete_course = True
    can_edit_course_roles = True
    can_add_course_users = True
    can_delete_course_users = True
    can_add_course_user_group = True
    can_delete_course_user_group = True
    can_add_assignment = True
    can_delete_assignment = True
    can_edit_assignment = True
    can_manage_journals = True
    can_comment = True
    can_edit_staff_comment = True
    can_view_grade_history = True
    can_post_teacher_entries = True
    can_manage_journal_import_requests = True
