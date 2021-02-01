import Vue from 'vue'
import auth from '@/api/auth.js'
import router from '@/router/index.js'

function fromCache ({ state, commit }, cache, cacheKey, fn, force = false) {
    if (!(cacheKey in state[cache]) || force) {
        commit('UPDATE_CACHE', { cache, cacheKey, data: fn() })
    }

    return state[cache][cacheKey]
}

function propogateTemplateCategoryUpdate (categories, updatedTemplate, oldTemplateId) {
    categories.forEach((category) => {
        const categoryTemplateIndex = category.templates.findIndex(
            template => template.id === updatedTemplate.id || template.id === oldTemplateId)
        const categoryLinkedToTemplate = categoryTemplateIndex !== -1

        if (categoryLinkedToTemplate) {
            Vue.set(category.templates, categoryTemplateIndex, updatedTemplate)
        }

        const updatedTemplateLinkedToCategory = updatedTemplate.categories.find(elem => elem.id === category.id)

        if (!categoryLinkedToTemplate && updatedTemplateLinkedToCategory) {
            category.templates.push(updatedTemplate)
        } else if (categoryLinkedToTemplate && !updatedTemplateLinkedToCategory) {
            Vue.delete(category.templates, categoryTemplateIndex)
        }
    })
}

function propogateTemplateDelete (categories, deletedTemplateId) {
    categories.forEach((category) => {
        const categoryTemplateIndex = category.templates.findIndex(template => template.id === deletedTemplateId)

        if (categoryTemplateIndex !== -1) {
            Vue.delete(category.templates, categoryTemplateIndex)
        }
    })
}

const getters = {
    assignmentCategories: (state) => {
        const aID = router.currentRoute.params.aID
        if (aID in state.assignmentsCategories) { return state.assignmentsCategories[aID] }
        return []
    },
    assignmentHasCategories: (state) => {
        const aID = router.currentRoute.params.aID

        if (aID in state.assignmentsCategories) {
            return state.assignmentsCategories[aID].some(category => 'id' in category && category.id >= 0)
        }

        return false
    },
    assignmentsCategories: state => state.assignmentCategories,
    filteredCategories: state => state.filteredCategories,
    timelineInstance: state => state.timelineInstance,
}

const mutations = {
    UPDATE_CACHE (state, { cache, cacheKey, data }) {
        Vue.set(state[cache], cacheKey, data)
    },
    SET_ASSIGNMENT_CATEGORIES (state, { aID, categories }) {
        Vue.set(state.assignmentsCategories, aID, categories)
    },
    ADD_ASSIGNMENT_CATEGORY (state, { aID, category }) {
        state.assignmentsCategories[aID].push(category)
        state.assignmentsCategories[aID].sort((a, b) => a.name.localeCompare(b.name))
    },
    UPDATE_ASSIGNMENT_CATEGORY (state, { aID, category, oldId }) {
        const updatedCategoryIndex = state.assignmentsCategories[aID].findIndex(elem => elem.id === oldId)
        Vue.set(state.assignmentsCategories[aID], updatedCategoryIndex, category)
        state.assignmentsCategories[aID].sort((a, b) => a.name.localeCompare(b.name))
    },
    DELETE_ASSIGNMENT_CATEGORY (state, { aID, id }) {
        Vue.delete(
            state.assignmentsCategories[aID],
            state.assignmentsCategories[aID].findIndex(elem => elem.id === id),
        )
    },
    SET_ID_OF_CREATED_CATEGORY (state, { category, id }) {
        category.id = id
    },
    SET_FILTERED_CATEGORIES (state, filteredCategories) {
        state.filteredCategories = filteredCategories
    },
    CLEAR_FILTERED_CATEGORIES (state) {
        state.filteredCategories = []
    },
    SET_TIMELINE_INSTANCE (state, instance) {
        state.timelineInstance = instance
    },
    PROPOGATE_TEMPLATE_CATEGORY_UPDATE (state, { aID, updatedTemplate, oldTemplateId }) {
        propogateTemplateCategoryUpdate(state.assignmentsCategories[aID], updatedTemplate, oldTemplateId)
    },
    PROPOGATE_TEMPLATE_DELETE (state, { aID, deletedTemplateId }) {
        propogateTemplateDelete(state.assignmentsCategories[aID], deletedTemplateId)
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
                    context.commit('SET_ASSIGNMENT_CATEGORIES', { aID, categories: response.data.categories })
                    return response.data.categories
                })
        }

        return fromCache(context, 'listCache', aID, fn.bind(null), force)
    },
    /* NOTE: Plain create is currently unused */
    create (context, { category, aID, connArgs = auth.DEFAULT_CONN_ARGS }) { // eslint-disable-line
        function fn () {
            /* Create a payload so we do not modify the local categories templates directly */
            const payload = JSON.parse(JSON.stringify(category))
            payload.templates = payload.templates.map(elem => elem.id)
            payload.assignment_id = aID

            return auth.create('categories', payload, connArgs)
                .then((response) => {
                    const createdCategory = response.data.category

                    context.commit(
                        'ADD_ASSIGNMENT_CATEGORY',
                        { aID: router.currentRoute.params.aID, category: createdCategory },
                    )
                    context.commit(
                        'template/PROPOGATE_CATEGORY_TEMPLATE_UPDATE',
                        { aID: router.currentRoute.params.aID, updatedCategory: createdCategory },
                        { root: true },
                    )

                    context.state.timelineInstance.syncNodes()

                    return createdCategory
                })
        }

        return fn()
    },
    update (context, { id, category, aID, connArgs = auth.DEFAULT_CONN_ARGS }) { // eslint-disable-line
        function fn () {
            /* Create a payload so we do not modify the local categories templates directly */
            const payload = JSON.parse(JSON.stringify(category))
            payload.templates = payload.templates.map(elem => elem.id)
            payload.assignment_id = aID

            return auth.update(`categories/${id}`, payload, connArgs)
                .then((response) => {
                    const updatedCategory = response.data.category

                    context.commit('UPDATE_ASSIGNMENT_CATEGORY', { aID, category: updatedCategory, oldId: id })
                    context.commit(
                        'template/PROPOGATE_CATEGORY_TEMPLATE_UPDATE',
                        { aID, updatedCategory },
                        { root: true },
                    )
                    context.state.timelineInstance.syncNodes()

                    return updatedCategory
                })
        }

        return fn()
    },
    delete (context, { id, force = true, connArgs = auth.DEFAULT_CONN_ARGS }) {
        const aID = router.currentRoute.params.aID

        function fn () {
            return auth.delete(`categories/${id}`, null, connArgs)
                .then((response) => {
                    const updatedFilteredCategories = context.getters.filteredCategories.filter(elem => elem.id !== id)

                    context.commit('SET_FILTERED_CATEGORIES', updatedFilteredCategories)
                    context.commit('DELETE_ASSIGNMENT_CATEGORY', { aID, id })
                    context.commit('template/PROPOGATE_CATEGORY_DELETE', { aID, deletedCategoryId: id }, { root: true })

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
        filteredCategories: [], /* Filter used for the timeline */
        timelineInstance: null,
    },
    getters,
    mutations,
    actions,
    propogateTemplateCategoryUpdate,
    propogateTemplateDelete,
}
