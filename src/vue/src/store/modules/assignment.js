import assignmentAPI from '@/api/assignment.js'

function fromCache ({ state, commit }, cache, cacheKey, fn, force = false) {
    if (!(cacheKey in state[cache]) || force) {
        commit('updateCache', { cache, cacheKey, data: fn() })
    }

    return state[cache][cacheKey]
}

const mutations = {
    updateCache (state, { cache, cacheKey, data }) {
        state[cache][cacheKey] = data
    },
}

const actions = {
    retrieve (context, { id, force = false }) {
        const fn = assignmentAPI.get.bind(null, id)
        return fromCache(context, 'retrieveCache', id, fn, force)
    },
}

export default {
    namespaced: true,
    state: {
        retrieveCache: {},
    },
    mutations,
    actions,
}
