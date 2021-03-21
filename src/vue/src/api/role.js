import auth from '@/api/auth.js'

export default {
    update (cID, data, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.update(`roles/${cID}`, { roles: data }, connArgs)
            .then((response) => response.data.role)
    },

    delete (cID, name, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.delete(`roles/${cID}`, { name }, connArgs)
            .then((response) => response.data)
    },

    getFromCourse (cID, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.get('roles', { course_id: cID }, connArgs)
            .then((response) => response.data.roles)
    },
}
