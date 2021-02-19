import auth from '@/api/auth.js'

export default {
    update (id, data, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.update(`preferences/${id}`, data, connArgs)
            .then((response) => response.data.preferences)
    },
}
