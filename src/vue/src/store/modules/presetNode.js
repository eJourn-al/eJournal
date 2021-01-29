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
    assignmentPresetNodes: (state) => {
        const aID = router.currentRoute.params.aID
        if (aID in state.assignmentsPresetNodes) { return state.assignmentsPresetNodes[aID] }
        return []
    },
    assignmentsPresetNodes: state => state.assignmentsPresetNodes,
}

const mutations = {
    UPDATE_CACHE (state, { cache, cacheKey, data }) {
        Vue.set(state[cache], cacheKey, data)
    },
    SET_ASSIGNMENT_PRESET_NODES (state, { aID, presetNodes }) {
        Vue.set(state.assignmentsPresetNodes, aID, presetNodes)
    },
    ADD_ASSIGNMENT_PRESET_NODE (state, { aID, presetNode }) {
        state.assignmentsPresetNodes[aID].push(presetNode)
        state.assignmentsPresetNodes[aID].sort((a, b) => new Date(a.due_date) - new Date(b.due_date))
    },
    UPDATE_ASSIGNMENT_PRESET_NODE (state, { aID, presetNode }) {
        const updatedPresetNodeIndex = state.assignmentsPresetNodes[aID].findIndex(elem => elem.id === presetNode.id)

        Vue.set(state.assignmentsPresetNodes[aID], updatedPresetNodeIndex, presetNode)
        state.assignmentsPresetNodes[aID].sort((a, b) => new Date(a.due_date) - new Date(b.due_date))
    },
    DELETE_ASSIGNMENT_PRESET_NODE (state, { aID, id }) {
        Vue.delete(
            state.assignmentsPresetNodes[aID],
            state.assignmentsPresetNodes[aID].findIndex(elem => elem.id === id),
        )
    },
}

const actions = {
    list (context, { aID, force = false, connArgs = auth.DEFAULT_CONN_ARGS }) {
        function fn () {
            return auth.get('preset_nodes', { assignment_id: aID }, connArgs)
                .then((response) => {
                    context.commit('SET_ASSIGNMENT_PRESET_NODES', { aID, presetNodes: response.data.presets })
                    return response.data.presets
                })
        }

        return fromCache(context, 'listCache', aID, fn.bind(null), force)
    },
    create (context, { data, aID, connArgs = auth.DEFAULT_CONN_ARGS }) {
        function fn () {
            data.assignment_id = aID

            return auth.create('preset_nodes', data, connArgs)
                .then((response) => {
                    context.commit('ADD_ASSIGNMENT_PRESET_NODE', { aID, presetNode: response.data.preset })
                    // TODO Category: does the timeline reactively filter after adding a preset node?
                    return response.data.preset
                })
        }

        return fn()
    },
    update (context, { data, aID, connArgs = auth.DEFAULT_CONN_ARGS }) { // eslint-disable-line
        function fn () {
            return auth.update(`preset_nodes/${data.id}`, data, connArgs)
                .then((response) => {
                    context.commit('UPDATE_ASSIGNMENT_PRESET_NODE', { aID, presetNode: response.data.preset })
                    // TODO Category: does the timeline reactively filter after updating a preset node?
                    return response.data.preset
                })
        }

        return fn()
    },
    delete (context, { id, aID, force = false, connArgs = auth.DEFAULT_CONN_ARGS }) { // eslint-disable-line
        function fn () {
            return auth.delete(`preset_nodes/${id}`, null, connArgs)
                .then((response) => {
                    context.commit('DELETE_ASSIGNMENT_PRESET_NODE', { id, aID })

                    return response.data
                })
        }

        return fromCache(context, 'deleteCache', id, fn.bind(null), force)
    },
}

export default {
    namespaced: true,
    state: {
        assignmentsPresetNodes: {},
        listCache: {},
        deleteCache: {},
    },
    getters,
    mutations,
    actions,
}
