import auth from '@/api/auth.js'

export default {
    list (cID, aID, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.get('journals', { course_id: cID, assignment_id: aID }, connArgs)
            .then(response => response.data.journals)
    },

    get (id, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.get(`journals/${id}`, null, connArgs)
            .then(response => response.data.journal)
    },

    create (data, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.create('journals', data, connArgs)
            .then(response => response.data.journals)
    },

    update (id, data, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.update(`journals/${id}`, data, connArgs)
            .then(response => response.data.journal)
    },

    delete (id, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.delete(`journals/${id}`, null, connArgs)
            .then(response => response.data)
    },

    join (id, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.update(`journals/${id}/join`, null, connArgs)
            .then(response => response.data.journal)
    },

    leave (id, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.update(`journals/${id}/leave`, null, connArgs)
            .then(response => response.data)
    },

    getMembers (id, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.get(`journals/${id}/get_members`, null, connArgs)
            .then(response => response.data.authors)
    },

    addMembers (id, userIds, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.update(`journals/${id}/add_members`, { user_ids: userIds }, connArgs)
            .then(response => response.data.authors)
    },

    kick (id, userId, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.update(`journals/${id}/kick`, { user_id: userId }, connArgs)
            .then(response => response.data)
    },

    lock (id, locked, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.update(`journals/${id}/lock`, { locked }, connArgs)
            .then(response => response.data)
    },

    getNodes (id, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.get('nodes', { journal_id: id }, connArgs)
            .then(response => response.data.nodes)
    },

    getFromAssignment (cID, aID, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.get('journals', { course_id: cID, assignment_id: aID }, connArgs)
            .then(response => response.data.journals)
    },
}
