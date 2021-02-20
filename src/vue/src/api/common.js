import auth from '@/api/auth.js'

export default {
    /* Common file for multi-purpose api calls. */
    getNames (data, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.get(`names/${data.cID || 0}/${data.aID || 0}/${data.jID || 0}`, null, connArgs)
            .then((response) => response.data.names)
    },

    getPermissions (courseID, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.get('roles/0', { course_id: courseID }, connArgs)
            .then((response) => response.data.role)
    },
}
