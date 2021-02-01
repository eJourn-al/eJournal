import Vue from 'vue'
import auth from '@/api/auth.js'
import router from '@/router/index.js'

function fromCache ({ state, commit }, cache, cacheKey, fn, force = false) {
    if (!(cacheKey in state[cache]) || force) {
        commit('UPDATE_CACHE', { cache, cacheKey, data: fn() })
    }

    return state[cache][cacheKey]
}

function propogateCategoryTemplateUpdate (templates, updatedCategory) {
    templates.forEach((template) => {
        const templateCategoryIndex = template.categories.findIndex(category => category.id === updatedCategory.id)
        const templateLinkedToCategory = templateCategoryIndex !== -1

        if (templateLinkedToCategory) {
            Vue.set(template.categories, templateCategoryIndex, updatedCategory)
        }

        const updatedCategoryLinkedToTemplate = updatedCategory.templates.find(elem => elem.id === template.id)

        if (!templateLinkedToCategory && updatedCategoryLinkedToTemplate) {
            template.categories.push(updatedCategory)
        } else if (templateLinkedToCategory && !updatedCategoryLinkedToTemplate) {
            Vue.delete(template.categories, templateCategoryIndex)
        }
    })
}

function propogateCategoryDelete (templates, deletedCategoryId) {
    templates.forEach((template) => {
        const templateCategoryIndex = template.categories.findIndex(category => category.id === deletedCategoryId)

        if (templateCategoryIndex !== -1) {
            Vue.delete(template.categories, templateCategoryIndex)
        }
    })
}

const getters = {
    assignmentTemplates: (state) => {
        const aID = router.currentRoute.params.aID
        if (aID in state.assignmentsTemplates) { return state.assignmentsTemplates[aID] }
        return []
    },
    assignmentsTemplates: state => state.assignmentsTemplates,
    timelineInstance: state => state.timelineInstance,
}

const mutations = {
    UPDATE_CACHE (state, { cache, cacheKey, data }) {
        Vue.set(state[cache], cacheKey, data)
    },
    SET_ASSIGNMENT_TEMPLATES (state, { aID, templates }) {
        Vue.set(state.assignmentsTemplates, aID, templates)
    },
    ADD_ASSIGNMENT_TEMPLATE (state, { aID, template }) {
        state.assignmentsTemplates[aID].push(template)
        state.assignmentsTemplates[aID].sort((a, b) => a.name.localeCompare(b.name))
    },
    UPDATE_ASSIGNMENT_TEMPLATE (state, { aID, template, oldId }) {
        const updatedTemplateIndex = state.assignmentsTemplates[aID].findIndex(elem => elem.id === oldId)
        Vue.set(state.assignmentsTemplates[aID], updatedTemplateIndex, template)
        state.assignmentsTemplates[aID].sort((a, b) => a.name.localeCompare(b.name))
    },
    DELETE_ASSIGNMENT_TEMPLATE (state, { aID, id }) {
        Vue.delete(
            state.assignmentsTemplates[aID],
            state.assignmentsTemplates[aID].findIndex(elem => elem.id === id),
        )
    },
    PROPOGATE_CATEGORY_TEMPLATE_UPDATE (state, { aID, updatedCategory }) {
        propogateCategoryTemplateUpdate(state.assignmentsTemplates[aID], updatedCategory)
    },
    PROPOGATE_CATEGORY_DELETE (state, { aID, deletedCategoryId }) {
        propogateCategoryDelete(state.assignmentsTemplates[aID], deletedCategoryId)
    },
}

const actions = {
    list (context, { aID, force = false, connArgs = auth.DEFAULT_CONN_ARGS }) {
        function fn () {
            return auth.get('templates', { assignment_id: aID }, connArgs)
                .then((response) => {
                    context.commit('SET_ASSIGNMENT_TEMPLATES', { aID, templates: response.data.templates })
                    return response.data.templates
                })
        }

        return fromCache(context, 'listCache', aID, fn.bind(null), force)
    },
    create (context, { template, aID, templateImport = false, connArgs = auth.DEFAULT_CONN_ARGS }) { // eslint-disable-line
        function fn () {
            const payload = JSON.parse(JSON.stringify(template))
            payload.assignment_id = aID
            payload.template_import = templateImport

            return auth.create('templates', payload, connArgs)
                .then((response) => {
                    const createdTemplate = response.data.template

                    context.commit('ADD_ASSIGNMENT_TEMPLATE', { aID, template: createdTemplate })
                    context.commit(
                        'category/PROPOGATE_TEMPLATE_CATEGORY_UPDATE',
                        { aID, updatedTemplate: createdTemplate },
                        { root: true },
                    )

                    return createdTemplate
                })
        }

        return fn()
    },
    update (context, { id, data, aID, connArgs = auth.DEFAULT_CONN_ARGS }) { // eslint-disable-line
        function fn () {
            return auth.update(`templates/${id}`, data, connArgs)
                .then((response) => {
                    const updatedTemplate = response.data.template

                    context.commit('UPDATE_ASSIGNMENT_TEMPLATE', { aID, template: updatedTemplate, oldId: id })
                    context.commit(
                        'category/PROPOGATE_TEMPLATE_CATEGORY_UPDATE',
                        { aID, updatedTemplate, oldTemplateId: id },
                        { root: true },
                    )

                    return updatedTemplate
                })
        }

        return fn()
    },
    delete (context, { id, aID, force = true, connArgs = auth.DEFAULT_CONN_ARGS }) { // eslint-disable-line
        function fn () {
            return auth.delete(`templates/${id}`, null, connArgs)
                .then((response) => {
                    context.commit('DELETE_ASSIGNMENT_TEMPLATE', { id, aID })
                    context.commit('category/PROPOGATE_TEMPLATE_DELETE', { aID, deletedTemplateId: id }, { root: true })

                    return response.data
                })
        }

        return fromCache(context, 'deleteCache', id, fn.bind(null), force)
    },
}

export default {
    namespaced: true,
    state: {
        assignmentsTemplates: {},
        listCache: {},
        deleteCache: {},
    },
    getters,
    mutations,
    actions,
    propogateCategoryTemplateUpdate,
    propogateCategoryDelete,
}
