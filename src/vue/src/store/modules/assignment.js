import assignmentAPI from '@/api/assignment.js'
import router from '@/router/index.js'

function cache ({ state, commit }, id, fn, force = false) {
    if (!('aID' in state.assignments) || force) {
        commit('setAssignment', { id, assignment: fn() })
    }

    return state.assignments[id]
}

const getters = {
    assignments: state => state.assignments,
    assignment (state) {
        return state.assignments[router.currentRoute.params.aID]
    },
}

const mutations = {
    setAssignment (state, { id, assignment }) {
        state.assignments[id] = assignment
    },
}

const actions = {
    retrieve (context, { id, force = false }) {
        const fn = assignmentAPI.get.bind(null, id)
        return cache(context, id, fn, force)
    },
}

export default {
    namespaced: true,
    state: {
        assignments: {},
    },
    getters,
    mutations,
    actions,
}
