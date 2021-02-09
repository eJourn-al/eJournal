import Vue from 'vue'
import auth from '@/api/auth.js'

const getters = {
    assignment: (state, _, rootState) => {
        const aID = rootState.route.params.aID
        if (aID in state.assignments) { return state.assignments[aID] }
        return null
    },
}

const mutations = {
    SET_ASSIGNMENT (state, { assignment }) {
        Vue.set(state.assignments, assignment.id, assignment)
    },
}

const actions = {
    retrieve (context, { id, cID = null, force = false, connArgs = auth.DEFAULT_CONN_ARGS }) {
        function fn () {
            return auth.get(`assignments/${id}`, { course_id: cID }, connArgs)
                .then((response) => {
                    context.commit('SET_ASSIGNMENT', { assignment: response.data.assignment })
                    return response.data.assignment
                })
        }

        return context.dispatch('fromCache', { cache: 'retrieveCache', cacheKey: id, fn: fn.bind(null), force })
    },
    update (context, { id, data, cID = null, connArgs = auth.DEFAULT_CONN_ARGS }) {
        function fn () {
            return auth.update(`assignments/${id}`, { course_id: cID, ...data }, connArgs)
                .then((response) => {
                    context.commit('SET_ASSIGNMENT', { assignment: response.data.assignment })

                    return response.data.assignment
                })
        }

        return fn()
    },
}

export default {
    namespaced: true,
    state: {
        assignments: {},
        retrieveCache: {},
    },
    getters,
    mutations,
    actions,
}
