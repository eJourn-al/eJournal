import Vue from 'vue'

export default {
    mutations: {
        UPDATE_CACHE (state, { cache, cacheKey, data }) {
            Vue.set(state[cache], cacheKey, data)
        },
    },

    actions: {
        fromCache (context, { cache, cacheKey, fn, force }) {
            if (!(cacheKey in context.state[cache]) || force) {
                context.commit('UPDATE_CACHE', { cache, cacheKey, data: fn() })
            }

            return context.state[cache][cacheKey]
        },
    },
}
