import auth from '@/api/auth.js'

export default {
    get (id, cID, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.get(`formats/${id}`, { course_id: cID }, connArgs)
            .then(response => response.data)
    },

    update (id, data, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.update(`formats/${id}`, data, connArgs)
            .then(response => response.data)
    },
}
