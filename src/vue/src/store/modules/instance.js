import Vue from 'vue'
import auth from '@/api/auth.js'

const getters = {
    instance: (state) => state.instance,
    allowRegistration: (state) => (state.instance ? state.instance.allow_standalone_registration : null),
    name: (state) => (state.instance ? state.instance.name : null),
    kalturaUrl: (state) => (state.instance ? state.instance.kaltura_url : null),
}

const mutations = {
    SET_INSTANCE (state, { instance }) {
        Vue.set(state, 'instance', instance)
    },
}

const actions = {
    retrieve (context, { force = false, connArgs = auth.DEFAULT_CONN_ARGS }) {
        if (!context.state.instance || force) {
            return auth.get('instance/0', null, connArgs)
                .then((response) => {
                    context.commit('SET_INSTANCE', { instance: response.data.instance })
                    return response.data.instance
                })
        } else {
            return context.state.instance
        }
    },
    update (context, { data, connArgs = auth.DEFAULT_CONN_ARGS }) {
        return auth.update('instance/0', data, connArgs)
            .then((response) => {
                context.commit('SET_INSTANCE', { instance: response.data.instance })

                return response.data.instance
            })
    },
}

export default {
    namespaced: true,
    state: {
        instance: null,
    },
    getters,
    mutations,
    actions,
}
