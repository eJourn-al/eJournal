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
    assignmentTemplates: (state) => {
        const aID = router.currentRoute.params.aID
        if (aID in state.assignmentsTemplates) { return state.assignmentsTemplates[aID] }
        return []
    },
    assignmentsTemplates: state => state.assignmentsTemplates,
    timelineInstance: state => state.timelineInstance,
}

const mutations = {
    updateCache (state, { cache, cacheKey, data }) {
        Vue.set(state[cache], cacheKey, data)
    },
    setAssignmentTemplates (state, { aID, templates }) {
        Vue.set(state.assignmentsTemplates, aID, templates)
    },
    // TODO: Add and update should do so whilest ordering based on template name?
    addAssignmentTemplate (state, { aID, template }) {
        state.assignmentsTemplates[aID].push(template)
    },
    updateAssignmentTemplate (state, { aID, template, oldId }) {
        const updatedTemplateIndex = state.assignmentsTemplates[aID].findIndex(elem => elem.id === oldId)
        Vue.set(state.assignmentsTemplates[aID], updatedTemplateIndex, template)
    },
    deleteAssignmentTemplate (state, { aID, id }) {
        Vue.delete(
            state.assignmentsTemplates[aID],
            state.assignmentsTemplates[aID].findIndex(elem => elem.id === id),
        )
    },
    /* TODO if needed, Make a timeline module which just contains the state of the active instance
     * Could also contain the active filter (category) */
    setTimelineInstance (state, instance) {
        state.timelineInstance = instance
    },
    propogateCategoryTemplateUpdate (state, { aID, updatedCategory }) {
        state.assignmentsTemplates[aID].forEach((template) => {
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
    },
}

const actions = {
    list (context, { aID, force = false, connArgs = auth.DEFAULT_CONN_ARGS }) {
        function fn () {
            return auth.get('templates', { assignment_id: aID }, connArgs)
                .then((response) => {
                    context.commit('setAssignmentTemplates', { aID, templates: response.data.templates })
                    return response.data.templates
                })
        }

        return fromCache(context, 'listCache', aID, fn.bind(null), force)
    },
    create (context, { template, aID, connArgs = auth.DEFAULT_CONN_ARGS }) {
        function fn () {
            const payload = JSON.parse(JSON.stringify(template))
            payload.assignment_id = aID

            return auth.create('templates', payload, connArgs)
                .then((response) => {
                    const createdTemplate = response.data.template

                    context.commit('addAssignmentTemplate', { aID, template: createdTemplate })
                    context.commit(
                        'category/propogateTemplateCategoryUpdate',
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

                    context.commit('updateAssignmentTemplate', { aID, template: updatedTemplate, oldId: id })
                    context.commit(
                        'category/propogateTemplateCategoryUpdate',
                        { aID, updatedTemplate, oldTemplateId: id },
                        { root: true },
                    )

                    return updatedTemplate
                })
        }

        return fn()
    },
    delete (context, { id, aID, force = false, connArgs = auth.DEFAULT_CONN_ARGS }) { // eslint-disable-line
        function fn () {
            return auth.delete(`templates/${id}`, null, connArgs)
                .then((response) => {
                    context.commit('deleteAssignmentTemplate', { id, aID })
                    context.commit('category/propogateTemplateDelete', { aID, deletedTemplateId: id }, { root: true })

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
}
