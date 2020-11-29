import auth from '@/api/auth.js'

export default {
    get (id, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.get(`courses/${id}`, null, connArgs)
            .then(response => response.data.course)
    },

    create (data, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.create('courses', data, connArgs)
            .then(response => response.data.course)
    },

    update (id, data, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.update(`courses/${id}`, data, connArgs)
            .then(response => response.data.course)
    },

    delete (id, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.delete(`courses/${id}`, null, connArgs)
            .then(response => response.data)
    },

    list (data = { get_all: false }, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.get('courses', data, connArgs)
            .then(response => response.data.courses)
    },

    getLinkable (connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.get('courses/linkable', null, connArgs)
            .then(response => response.data.courses)
    },
}
