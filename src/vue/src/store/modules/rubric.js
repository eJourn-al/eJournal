import Vue from 'vue'
import auth from '@/api/auth.js'

const getters = {
    assignmentRubrics: (state, _, rootState) => {
        const aID = rootState.route.params.aID
        if (aID in state.assignmentsRubrics) { return state.assignmentsRubrics[aID] }
        return []
    },
    assignmentsRubrics: (state) => state.assignmentsRubrics,
}

const mutations = {
    SET_ASSIGNMENT_RUBRICS (state, { aID, rubrics }) {
        Vue.set(state.assignmentsRubrics, aID, rubrics)
    },
    ADD_ASSIGNMENT_RUBRIC (state, { aID, rubric }) {
        state.assignmentsRubrics[aID].push(rubric)
        state.assignmentsRubrics[aID].sort((a, b) => a.name.localeCompare(b.name))
    },
    UPDATE_ASSIGNMENT_RUBRIC (state, { aID, rubric, oldId }) {
        const updatedRubricIndex = state.assignmentsRubrics[aID].findIndex((elem) => elem.id === oldId)
        Vue.set(state.assignmentsRubrics[aID], updatedRubricIndex, rubric)
        state.assignmentsRubrics[aID].sort((a, b) => a.name.localeCompare(b.name))
    },
    DELETE_ASSIGNMENT_RUBRIC (state, { aID, id }) {
        Vue.delete(
            state.assignmentsRubrics[aID],
            state.assignmentsRubrics[aID].findIndex((elem) => elem.id === id),
        )
    },
}

const actions = {
    list (context, { aID, force = false, connArgs = auth.DEFAULT_CONN_ARGS }) {
        function fn () {
            return auth.get('rubrics', { assignment_id: aID }, connArgs)
                .then((response) => {
                    context.commit('SET_ASSIGNMENT_RUBRICS', { aID, rubrics: response.data.rubrics })
                    return response.data.rubrics
                })
        }

        return context.dispatch('fromCache', { cache: 'listCache', cacheKey: aID, fn: fn.bind(null), force })
    },
    create (context, { rubric, aID, templateImport = false, connArgs = auth.DEFAULT_CONN_ARGS }) {
        function fn () {
            const payload = JSON.parse(JSON.stringify(rubric))
            payload.assignment_id = aID
            payload.template_import = templateImport

            return auth.create('rubrics', payload, connArgs)
                .then((response) => {
                    const createdRubric = response.data.rubric

                    context.commit('ADD_ASSIGNMENT_RUBRIC', { aID, rubric: createdRubric })

                    return createdRubric
                })
        }

        return fn()
    },
    update (context, { id, data, aID, connArgs = auth.DEFAULT_CONN_ARGS }) {
        function fn () {
            return auth.update(`rubrics/${id}`, data, connArgs)
                .then((response) => {
                    const updatedRubric = response.data.rubric

                    context.commit('UPDATE_ASSIGNMENT_RUBRIC', { aID, rubric: updatedRubric, oldId: id })

                    return updatedRubric
                })
        }

        return fn()
    },
    delete (context, { id, aID, force = true, connArgs = auth.DEFAULT_CONN_ARGS }) {
        function fn () {
            return auth.delete(`rubrics/${id}`, null, connArgs)
                .then((response) => {
                    context.commit('DELETE_ASSIGNMENT_RUBRIC', { id, aID })

                    return response.data
                })
        }

        return context.dispatch('fromCache', { cache: 'deleteCache', cacheKey: id, fn: fn.bind(null), force })
    },
}

export default {
    namespaced: true,
    state: {
        assignmentsRubrics: {},
        listCache: {},
        deleteCache: {},
    },
    getters,
    mutations,
    actions,
}
