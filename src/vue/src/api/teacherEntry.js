import auth from '@/api/auth.js'

export default {
    update (id, data, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.update(`teacher_entries/${id}`, data, connArgs)
            .then((response) => response.data.teacher_entry)
    },

    create (data, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.create('teacher_entries', data, connArgs)
            .then((response) => response.data.teacher_entry)
    },

    delete (id, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.delete(`teacher_entries/${id}`, connArgs)
    },
}
