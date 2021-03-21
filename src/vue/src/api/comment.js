import auth from '@/api/auth.js'

export default {
    get (id, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.get(`comments/${id}`, null, connArgs)
            .then((response) => response.data.comment)
    },

    create (data, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.create('comments', data, connArgs)
            .then((response) => response.data.comment)
    },

    update (id, data, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.update(`comments/${id}`, data, connArgs)
            .then((response) => response.data.comment)
    },

    delete (id, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.delete(`comments/${id}`, null, connArgs)
            .then((response) => response.data)
    },

    getFromEntry (id, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.get('comments', { entry_id: id }, connArgs)
            .then((response) => response.data.comments)
    },
}
