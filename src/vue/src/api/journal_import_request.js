import auth from '@/api/auth.js'

export default {
    list (journalTargetID, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.get('journal_import_request', { journal_target_id: journalTargetID }, connArgs)
            .then(response => response.data.journal_import_requests)
    },

    create (data, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.create('journal_import_request', data, connArgs)
            .then(response => response.data.journal_import_request)
    },

    update (id, jirAction, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.update(`journal_import_request/${id}`, { jir_action: jirAction }, connArgs)
            .then(response => response.data)
    },
}
