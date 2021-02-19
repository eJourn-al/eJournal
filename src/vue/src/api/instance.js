import auth from '@/api/auth.js'

export default {
    get (connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.get('instance/0', null, connArgs)
            .then((response) => response.data.instance)
    },

    update (data, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.update('instance/0', data, connArgs)
            .then((response) => response.data.instance)
    },
}
