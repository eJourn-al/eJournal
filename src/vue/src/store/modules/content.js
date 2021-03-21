import * as types from '../constants/mutation-types.js'

const getters = {
    // Assignment data.
    assignmentParticipantsWithoutJournal: (state) => state.assignmentParticipantsWithoutJournal,
}

const mutations = {
    [types.SET_ASSIGNMENT_PARTICIPANTS_WITHOUT_JOURNAL] (state, val) {
        state.assignmentParticipantsWithoutJournal = val
    },
    [types.RESET_CONTENT] (state) {
        state.assignmentParticipantsWithoutJournal = []
    },
}

export default {
    namespaced: true,
    state: {
        assignmentParticipantsWithoutJournal: [],
    },
    getters,
    mutations,
}
