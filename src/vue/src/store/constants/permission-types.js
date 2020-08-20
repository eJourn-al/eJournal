export const GENERAL_LEVEL_PERMISSIONS = new Set([
    'can_edit_institute_details',
    'can_add_course',
])

export const COURSE_LEVEL_PERMISSIONS = new Set([
    'can_edit_course_details',
    'can_delete_course',
    'can_edit_course_roles',
    'can_view_course_users',
    'can_add_course_users',
    'can_delete_course_users',
    'can_add_course_user_group',
    'can_delete_course_user_group',
    'can_edit_course_user_group',
    'can_add_assignment',
    'can_delete_assignment',
])

export const ASSIGNMENT_LEVEL_PERMISSIONS = new Set([
    'can_edit_assignment',
    'can_view_all_journals',
    'can_grade',
    'can_publish_grades',
    'can_view_grade_history',
    'can_view_unpublished_assignment',
    // Journal level
    'can_manage_journals',
    'can_have_journal',
    'can_comment',
    'can_edit_staff_comment',
    'can_manage_journal_import_requests',
])

export const ALL_PERIMSSIONS = new Set([
    ...GENERAL_LEVEL_PERMISSIONS,
    ...COURSE_LEVEL_PERMISSIONS,
    ...ASSIGNMENT_LEVEL_PERMISSIONS,
])

export const PERMISSION_KEY_LEVELS = new Set([
    'general',
    'course',
    'assignment',
])
