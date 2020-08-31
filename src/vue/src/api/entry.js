import auth from '@/api/auth.js'

export default {
    create (data, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.create('entries', data, connArgs)
            .then(response => response.data)
    },

    update (id, data, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.update(`entries/${id}`, data, connArgs)
            .then(response => response.data.entry)
    },

    delete (id, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.delete(`entries/${id}`, null, connArgs)
            .then(response => response.data)
    },
}
