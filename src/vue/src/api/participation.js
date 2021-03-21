import auth from '@/api/auth.js'

export default {
    get (id, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.get(`participations/${id}`, null, connArgs)
            .then((response) => response.data.participant)
    },

    getEnrolled (id, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.get('participations', { course_id: id }, connArgs)
            .then((response) => response.data.participants)
    },

    create (data, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.create('participations', data, connArgs)
            .then((response) => response.data.participant)
    },

    update (id, data, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.update(`participations/${id}`, data, connArgs)
            .then((response) => response.data.participant)
    },

    delete (cID, uID, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.delete(`participations/${cID}`, { user_id: uID }, connArgs)
            .then((response) => response.data)
    },

    getUnenrolled (id, unenrolledQuery, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.get('participations/unenrolled', { course_id: id, unenrolled_query: unenrolledQuery }, connArgs)
            .then((response) => response.data.participants)
    },

}
