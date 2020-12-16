import auth from '@/api/auth.js'

export default {
    list (aID, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.get('categories', { assignment_id: aID }, connArgs)
            .then(response => response.data.categories)
    },

    get (id, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.get(`categories/${id}`, null, connArgs)
            .then(response => response.data.category)
    },

    create (data, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.create('categories', data, connArgs)
            .then(response => response.data.category)
    },

    update (id, data, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.update(`categories/${id}`, data, connArgs)
            .then(response => response.data.category)
    },

    delete (id, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.delete(`categories/${id}`, null, connArgs)
            .then(response => response.data)
    },

    editEntry (id, data, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.update(`categories/${id}/edit_entry`, data, connArgs)
            .then(response => response.data)
    },
}
