import Vue from 'vue'
import auth from '@/api/auth.js'
import router from '@/router/index.js'

function fromCache ({ state, commit }, cache, cacheKey, fn, force = false) {
    if (!(cacheKey in state[cache]) || force) {
        commit('updateCache', { cache, cacheKey, data: fn() })
    }

    return state[cache][cacheKey]
}

const getters = {
    assignmentCategories: (state) => {
        const aID = router.currentRoute.params.aID
        if (aID in state.assignmentsCategories) { return state.assignmentsCategories[aID] }
        return []
    },
    assignmentsCategories: state => state.assignmentCategories,
    filteredCategories: state => state.filteredCategories,
    timelineInstance: state => state.timelineInstance,
}

const mutations = {
    updateCache (state, { cache, cacheKey, data }) {
        Vue.set(state[cache], cacheKey, data)
    },
    updateAssignmentCategories (state, { aID, categories }) {
        Vue.set(state.assignmentsCategories, aID, categories)
    },
    addAssignmentCategory (state, { aID, category }) {
        state.assignmentsCategories[aID].push(category)
    },
    deleteAssignmentCategory (state, { aID, id }) {
        Vue.delete(
            state.assignmentsCategories[aID],
            state.assignmentsCategories[aID].findIndex(elem => elem.id === id),
        )
    },
    setIdOfCreatedCategory (state, { category, id }) {
        category.id = id
    },
    setFilteredCategories (state, filteredCategories) {
        state.filteredCategories = filteredCategories
    },
    clearFilteredCategories (state) {
        state.filteredCategories = []
    },
    setTimelineInstance (state, instance) {
        state.timelineInstance = instance
    },
}

const actions = {
    /* NOTE: Get is currently unused */
    get (context, { id, force = false, connArgs = auth.DEFAULT_CONN_ARGS }) { // eslint-disable-line
        return auth.get(`categories/${id}`, null, connArgs)
            .then(response => response.data.category)
    },
    list (context, { aID, force = false, connArgs = auth.DEFAULT_CONN_ARGS }) {
        function fn () {
            return auth.get('categories', { assignment_id: aID }, connArgs)
                .then((response) => {
                    context.commit('updateAssignmentCategories', { aID, categories: response.data.categories })
                    return response.data.categories
                })
        }

        return fromCache(context, 'listCache', aID, fn.bind(null), force)
    },
    /* NOTE: Plain create is currently unused */
    create (context, { data, connArgs = auth.DEFAULT_CONN_ARGS }) {
        function fn () {
            return auth.create('categories', data, connArgs)
                .then((response) => {
                    const createdCategory = response.data.category

                    context.commit(
                        'addAssignmentCategory',
                        { aID: router.currentRoute.params.aID, category: createdCategory },
                    )

                    context.state.timelineInstance.syncNodes()

                    return createdCategory
                })
        }

        return fn()
    },
    createAndOnlyUpdateId (context, { localCategory, aID, connArgs = auth.DEFAULT_CONN_ARGS }) {
        function fn () {
            const payload = JSON.parse(JSON.stringify(localCategory))

            /* Create a payload so we do not modify the localCategories templates directly */
            payload.templates = localCategory.templates.map(elem => elem.id)
            payload.assignment_id = aID

            return auth.create('categories', payload, connArgs)
                .then((response) => {
                    const createdCategory = response.data.category
                    context.commit('setIdOfCreatedCategory', { category: localCategory, id: createdCategory.id })

                    return createdCategory
                })
        }

        return fn()
    },
    update (context, { id, data, updateStore = false, connArgs = auth.DEFAULT_CONN_ARGS }) { // eslint-disable-line
        function fn () {
            return auth.update(`categories/${id}`, data, connArgs)
                .then((response) => {
                    const updatedCategory = response.data.category

                    if (updateStore) {
                        const aID = router.currentRoute.params.aID
                        const updatedCategories = context.state.assignmentCategories.map((category) => {
                            if (category.id === updatedCategory.id) {
                                return updatedCategory
                            }
                            return category
                        })

                        context.commit('updateAssignmentCategories', { aID, categories: updatedCategories })
                    }

                    context.state.timelineInstance.syncNodes()

                    return updatedCategory
                })
        }

        return fn()
    },
    delete (context, { id, force = false, connArgs = auth.DEFAULT_CONN_ARGS }) {
        function fn () {
            return auth.delete(`categories/${id}`, null, connArgs)
                .then((response) => {
                    const updatedFilteredCategories = context.getters.filteredCategories.filter(elem => elem.id !== id)

                    context.commit('setFilteredCategories', updatedFilteredCategories)
                    context.commit('deleteAssignmentCategory', { aID: router.currentRoute.params.aID, id })

                    return response.data
                })
        }

        return fromCache(context, 'deleteCache', id, fn.bind(null), force)
    },
    editEntry (context, { id, data, connArgs = auth.DEFAULT_CONN_ARGS }) {
        function fn () {
            return auth.update(`categories/${id}/edit_entry`, data, connArgs)
                .then(response => response.data)
        }

        return fn()
    },
}

export default {
    namespaced: true,
    state: {
        assignmentsCategories: {},
        listCache: {},
        deleteCache: {},
        filteredCategories: [],
        timelineInstance: null,
    },
    getters,
    mutations,
    actions,
}
