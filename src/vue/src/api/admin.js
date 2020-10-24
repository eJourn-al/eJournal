import auth from '@/api/auth.js'

export default {
    inviteUsers (data, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.post('admin/invite_users/', data, connArgs)
            .then(response => response.data)
    },

    getAllUsers (connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.post('admin/get_all_users', null, connArgs)
            .then(response => response.data.users)
    },

    removeUser (id, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.post(`admin/${id}/remove_user`, connArgs)
            .then(response => response.data)
    },

    updateTeacherStatus (id, data, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.post(`admin/${id}/update_teacher_status`, data, connArgs)
            .then(response => response.data)
    },
}
