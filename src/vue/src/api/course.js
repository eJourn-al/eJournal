import auth from '@/api/auth'

export default {
    /* Get user courses.
     * Requests all the users courses.
     * returns a list of all courses.
     */
    get_user_courses () {
        return auth.authenticatedGet('/get_user_courses/')
            .then(response => response.data.courses)
    },

    /* Get the user's permissions in a course. */
    get_course_permissions (cID) {
        return auth.authenticatedGet('/get_course_permissions/' + cID + '/')
            .then(response => response.data.permissions)

    /* Create a new course. */
    create_new_course (name, abbr, startdate) {
        return auth.authenticatedPost('/create_new_course/', {
            name: name,
            abbr: abbr,
            startdate: startdate
        }).then(response => response.data)
    }
}
