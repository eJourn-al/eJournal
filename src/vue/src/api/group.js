import auth from '@/api/auth.js'

export default {
    create (data, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.create('groups', data, connArgs)
            .then((response) => response.data.group)
    },

    update (id, data, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.update(`groups/${id}`, data, connArgs)
            .then((response) => response.data.group)
    },

    delete (id, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.delete(`groups/${id}`, null, connArgs)
    },

    getAllFromCourse (cID, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.get('groups', { course_id: cID }, connArgs)
            .then((response) => response.data.groups)
    },

    getFromAssignment (cID, aID, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.get('groups', { course_id: cID, assignment_id: aID }, connArgs)
            .then((response) => response.data.groups)
    },

    getAssignedGroups (cID, aID, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.get('groups/assigned_groups', { course_id: cID, assignment_id: aID }, connArgs)
            .then((response) => response.data.assigned_groups)
    },

    getDataNose (cID, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.get('groups/datanose', { course_id: cID }, connArgs)
            .then((response) => response.data.groups)
    },

    getLMS (cID, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.get('groups/LMS', { course_id: cID }, connArgs)
            .then((response) => {
                console.log(response)
                window.open(response.data.redirect_uri, '_blank')
            })
    },

    getMembers (gID, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.get('members', { group_id: gID }, connArgs)
            .then((response) => response.data.members)
    },

    removeMember (gID, uID, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.delete(`members/${gID}`, { user_id: uID }, connArgs)
            .then((response) => response.data.participants)
    },

    addMember (gID, uID, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.create('members', { group_id: gID, user_id: uID }, connArgs)
            .then((response) => response.data.participants)
    },
}
