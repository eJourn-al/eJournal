import auth from '@/api/auth.js'

export default {
    inviteUsers (data, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.post('admin/invite_users/', data, connArgs)
            .then(response => response.data)
    },

    importTemplate (id, data, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.post(`assignments/${id}/copytemplate/`, data, connArgs)
            .then(response => response.data.template)
    },

    getParticipantsWithoutJournal (id, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.get(`assignments/${id}/participants_without_journal`, null, connArgs)
            .then(response => response.data.participants)
    },

    getTemplates (id, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.get(`assignments/${id}/templates`, null, connArgs)
            .then(response => response.data.templates)
    },

    getTeacherEntries (id, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.get(`assignments/${id}/teacher_entries`, null, connArgs)
            .then(response => response.data.teacher_entries)
    },
}
