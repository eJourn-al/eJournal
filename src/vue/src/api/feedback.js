import auth from '@/api/auth.js'

export default {
    sendFeedback (data, config = {}, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.uploadFile('/send_feedback/', data, config, connArgs)
    },
}
