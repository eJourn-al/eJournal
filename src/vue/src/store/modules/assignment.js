import Vue from 'vue'
import auth from '@/api/auth.js'
import router from '@/router/index.js'

function fromCache ({ state, commit }, cache, cacheKey, fn, force = false) {
    if (!(cacheKey in state[cache]) || force) {
        commit('UPDATE_CACHE', { cache, cacheKey, data: fn() })
    }

    return state[cache][cacheKey]
}

const getters = {
    assignment: (state) => {
        const aID = router.currentRoute.params.aID
        if (aID in state.assignments) { return state.assignments[aID] }
        return null
    },
}

const mutations = {
    UPDATE_CACHE (state, { cache, cacheKey, data }) {
        Vue.set(state[cache], cacheKey, data)
    },
    SET_ASSIGNMENT (state, { assignment }) {
        Vue.set(state.assignments, assignment.id, assignment)
    },
}

const actions = {
    retrieve (context, { id, cID = null, force = false, connArgs = auth.DEFAULT_CONN_ARGS }) { // eslint-disable-line
        function fn () {
            return auth.get(`assignments/${id}`, { course_id: cID }, connArgs)
                .then((response) => {
                    context.commit('SET_ASSIGNMENT', { assignment: response.data.assignment })
                    return response.data.assignment
                })
        }

        return fromCache(context, 'retrieveCache', id, fn.bind(null), force)
    },
    update (context, { id, data, cID = null, connArgs = auth.DEFAULT_CONN_ARGS }) { // eslint-disable-line
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
