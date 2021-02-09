import Vue from 'vue'
import auth from '@/api/auth.js'

const getters = {
    assignmentPresetNodes: (state, _, rootState) => {
        const aID = rootState.route.params.aID
        if (aID in state.assignmentsPresetNodes) { return state.assignmentsPresetNodes[aID] }
        return []
    },
    assignmentsPresetNodes: state => state.assignmentsPresetNodes,
}

function propagateTemplatePresetNodeUpdate (presetNodes, updatedTemplate, oldTemplateId) {
    presetNodes.forEach((presetNode) => {
        if (presetNode.type !== 'd') { return }

        if (presetNode.template && presetNode.template.id === oldTemplateId) {
            // NOTE: Using reference here is safe, a presetNode cannot make changes to a template itself
            presetNode.template = updatedTemplate
        }
    })
}

const mutations = {
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
    PROPAGATE_TEMPLATE_PRESET_NODE_UPDATE (state, { aID, updatedTemplate, oldTemplateId }) {
        propagateTemplatePresetNodeUpdate(state.assignmentsPresetNodes[aID], updatedTemplate, oldTemplateId)
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

        return context.dispatch('fromCache', { cache: 'listCache', cacheKey: aID, fn: fn.bind(null), force })
    },
    create (context, { data, aID, connArgs = auth.DEFAULT_CONN_ARGS }) {
        function fn () {
            data.assignment_id = aID

            return auth.create('preset_nodes', data, connArgs)
                .then((response) => {
                    context.commit('ADD_ASSIGNMENT_PRESET_NODE', { aID, presetNode: response.data.preset })
                    return response.data.preset
                })
        }

        return fn()
    },
    update (context, { data, aID, connArgs = auth.DEFAULT_CONN_ARGS }) {
        function fn () {
            return auth.update(`preset_nodes/${data.id}`, data, connArgs)
                .then((response) => {
                    context.commit('UPDATE_ASSIGNMENT_PRESET_NODE', { aID, presetNode: response.data.preset })
                    return response.data.preset
                })
        }

        return fn()
    },
    delete (context, { id, aID, force = true, connArgs = auth.DEFAULT_CONN_ARGS }) {
        function fn () {
            return auth.delete(`preset_nodes/${id}`, null, connArgs)
                .then((response) => {
                    context.commit('DELETE_ASSIGNMENT_PRESET_NODE', { id, aID })

                    return response.data
                })
        }

        return context.dispatch('fromCache', { cache: 'deleteCache', cacheKey: id, fn: fn.bind(null), force })
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
    propagateTemplatePresetNodeUpdate,
}
