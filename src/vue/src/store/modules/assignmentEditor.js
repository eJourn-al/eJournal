import Vue from 'vue'
import colorUtils from '@/utils/colors.js'

const categorySymbol = Symbol('category')
const timelineSymbol = Symbol('timeline')
const templateSymbol = Symbol('template')
const templateImportSymbol = Symbol('templateImport')

const readSymbol = Symbol('read')
const editSymbol = Symbol('edit')

function fromDraft (drafts, obj) {
    if (obj.id in drafts) {
        const draft = drafts[obj.id]
        draft.edited = JSON.stringify(draft.draft) !== JSON.stringify(obj)

        return draft
    }

    const draft = { draft: JSON.parse(JSON.stringify(obj)), edited: false }
    drafts[obj.id] = draft

    return draft
}

const getters = {
    activeComponent: state => state.activeComponent,
    activeComponentOptions: state => state.activeComponentOptions,

    activeComponentMode: state => state.activeComponentMode,
    activeComponentModeOptions: state => state.activeComponentModeOptions,
    readMode: state => state.activeComponentMode === state.activeComponentModeOptions.read,
    editMode: state => state.activeComponentMode === state.activeComponentModeOptions.edit,

    assignmentDetailsDraft: state => state.assignmentDetailsDraft,

    selectedCategory: state => state.selectedCategory,
    newCategoryDraft: state => state.newCategoryDraft,

    selectedTemplate: state => state.selectedTemplate,
    newTemplateDraft: state => state.newTemplateDraft,

    selectedPresetNode: state => state.selectedPresetNode,
    newPresetNodeDraft: state => state.newPresetNodeDraft,

    selectedTimelineElementIndex: state => state.selectedTimelineElementIndex,
}

const mutations = {
    SET_ACTIVE_COMPONENT_MODE_TO_READ (state) {
        state.activeComponentMode = state.activeComponentModeOptions.read
    },
    SET_ACTIVE_COMPONENT_MODE_TO_EDIT (state) {
        state.activeComponentMode = state.activeComponentModeOptions.edit
    },

    SELECT_ASSIGNMENT_DETAILS (state, { originalAssignment }) {
        if (state.assignmentDetailsDraft) {
            const edited = JSON.stringify(originalAssignment) !== JSON.stringify(state.assignmentDetailsDraft)
            state.activeComponentMode = (edited)
                ? state.activeComponentModeOptions.edit : state.activeComponentModeOptions.read
        } else {
            state.assignmentDetailsDraft = JSON.parse(JSON.stringify(originalAssignment))
            state.activeComponentMode = state.activeComponentModeOptions.read
        }
    },
    CLEAR_ASSIGNMENT_DETAILS_DRAFT (state) {
        state.assignmentDetailsDraft = null
    },

    SELECT_CATEGORY (state, { category }) {
        const draft = fromDraft(state.categoryDrafts, category)

        state.selectedCategory = draft.draft
        state.activeComponent = state.activeComponentOptions.category
        state.activeComponentMode = (draft.edited)
            ? state.activeComponentModeOptions.edit : state.activeComponentModeOptions.read
    },
    CREATE_CATEGORY (state) {
        if (state.newCategoryDraft) {
            state.selectedCategory = state.newCategoryDraft
        } else {
            const newCategory = {
                id: -1,
                name: null,
                description: '',
                color: colorUtils.randomBrightRGBcolor(),
                templates: [],
            }

            state.selectedCategory = newCategory
            state.newCategoryDraft = newCategory
        }

        state.activeComponent = state.activeComponentOptions.category
        state.activeComponentMode = state.activeComponentModeOptions.edit
    },
    CLEAR_NEW_CATEGORY_DRAFT (state) {
        state.newCategoryDraft = null
    },
    CLEAR_SELECTED_CATEGORY (state) {
        Vue.delete(state.categoryDrafts, state.selectedCategory.id)
        state.selectedCategory = null
    },

    SELECT_TEMPLATE (state, { template }) {
        const draft = fromDraft(state.templateDrafts, template)

        state.selectedTemplate = draft.draft
        state.activeComponent = state.activeComponentOptions.template
        state.activeComponentMode = (draft.edited)
            ? state.activeComponentModeOptions.edit : state.activeComponentModeOptions.read
    },
    CREATE_TEMPLATE (state) {
        if (state.newTemplateDraft) {
            state.selectedTemplate = state.newTemplateDraft
        } else {
            const newTemplate = {
                field_set: [{
                    type: 'rt',
                    title: 'Content',
                    description: '',
                    options: null,
                    location: 0,
                    required: true,
                }],
                name: 'Entry',
                id: -1,
                preset_only: false,
                fixed_categories: true,
                categories: [],
            }

            state.selectedTemplate = newTemplate
            state.newTemplateDraft = newTemplate
        }

        state.activeComponent = state.activeComponentOptions.template
        state.activeComponentMode = state.activeComponentModeOptions.edit
    },
    CLEAR_NEW_TEMPLATE_DRAFT (state) {
        state.newTemplateDraft = null
    },
    SET_ACTIVE_COMPONENT_TO_TEMPLATE_IMPORT (state) {
        state.activeComponent = state.activeComponentOptions.templateImport
    },
    CLEAR_SELECTED_TEMPLATE (state) {
        Vue.delete(state.templateDrafts, state.selectedTemplate.id)
        state.selectedTemplate = null
    },

    SET_TIMELINE_ELEMENT_INDEX (state, { index }) {
        state.selectedTimelineElementIndex = index
    },
    SELECT_TIMELINE_ELEMENT (state, { timelineElementIndex, mode = editSymbol }) {
        state.selectedTimelineElementIndex = timelineElementIndex
        state.activeComponent = state.activeComponentOptions.timeline
        state.activeComponentMode = mode
    },
    CREATE_PRESET_NODE (state) {
        if (state.newPresetNodeDraft) {
            state.selectedPresetNode = state.newPresetNodeDraft
        } else {
            const newPreset = {
                id: -1,
                type: null,
                template: '',
                display_name: '',
                description: '',
                attached_files: [],
            }

            state.selectedPresetNode = newPreset
            state.newPresetNodeDraft = newPreset
        }

        state.activeComponent = state.activeComponentOptions.timeline
        state.activeComponentMode = state.activeComponentModeOptions.edit
    },
    SELECT_PRESET_NODE (state, { presetNode }) {
        const draft = fromDraft(state.presetNodeDrafts, presetNode)

        state.selectedPresetNode = draft.draft
        state.activeComponent = state.activeComponentOptions.timeline
        state.activeComponentMode = (draft.edited)
            ? state.activeComponentModeOptions.edit : state.activeComponentModeOptions.read
    },
    CLEAR_NEW_PRESET_NODE_DRAFT (state) {
        state.newPresetNodeDraft = null
    },
    CLEAR_SELECTED_PRESET_NODE (state) {
        Vue.delete(state.presetNodeDrafts, state.selectedPresetNode.id)
        state.selectedPresetNode = null
    },

    CLEAR_ACTIVE_COMPONENT (state) {
        state.activeComponentMode = state.activeComponentModeOptions.read
        state.activeComponent = state.activeComponentOptions.timeline
        state.selectedTimelineElementIndex = -1
    },
    CLEAR_DRAFT (state, { drafts, obj }) {
        Vue.delete(drafts, obj.id)
    },

    RESET (state) {
        state.selectedTimelineElementIndex = -1

        state.assignmentDetailsDraft = null

        state.selectedCategory = null
        state.newCategoryDraft = null
        state.categoryDrafts = {}

        state.selectedTemplate = null
        state.newTemplateDraft = null
        state.templateDrafts = {}

        state.selectedPresetNode = null
        state.newPresetNodeDraft = null
        state.presetNodeDrafts = {}
    },
}

const actions = {
    categoryCreated (context, { category }) {
        context.commit('CLEAR_NEW_CATEGORY_DRAFT')
        context.commit('SELECT_CATEGORY', { category })
    },
    templateCreated (context, { template }) {
        context.commit('CLEAR_NEW_TEMPLATE_DRAFT')
        context.commit('SELECT_TEMPLATE', { template })
    },

    categoryDeleted (context, { category }) {
        if (context.state.selectedCategory.id === category.id) {
            context.commit('CLEAR_ACTIVE_COMPONENT')
            context.commit('CLEAR_SELECTED_CATEGORY')
        }
    },
    presetNodeDeleted (context, { presetNode }) {
        if (context.state.selectedPresetNode.id === presetNode.id) {
            context.commit('CLEAR_ACTIVE_COMPONENT')
            context.commit('CLEAR_SELECTED_PRESET_NODE')
        }
    },
    templateDeleted (context, { template }) {
        if (context.state.selectedTemplate.id === template.id) {
            context.commit('CLEAR_ACTIVE_COMPONENT')
            context.commit('CLEAR_SELECTED_TEMPLATE')
        }
    },

    categoryUpdated (context, { category }) {
        context.commit('CLEAR_DRAFT', { drafts: context.state.categoryDrafts, obj: category })
        context.commit('SELECT_CATEGORY', { category })
    },
    presetNodeUpdated (context, { presetNode }) {
        context.commit('CLEAR_DRAFT', { drafts: context.state.presetNodeDrafts, obj: presetNode })
        context.commit('SELECT_PRESET_NODE', { presetNode })
    },
    templateUpdated (context, { template }) {
        context.commit('CLEAR_DRAFT', { drafts: context.state.templateDrafts, obj: template })
        context.commit('SELECT_TEMPLATE', { template })
    },

    timelineElementSelected (context, { timelineElementIndex, mode = editSymbol }) {
        context.commit('SELECT_TIMELINE_ELEMENT', { timelineElementIndex, mode })

        const presetNodes = context.rootGetters['presetNode/assignmentPresetNodes']

        /* Actual preset node selected */
        if (timelineElementIndex >= 0 && timelineElementIndex < presetNodes.length) {
            context.commit('SELECT_PRESET_NODE', { presetNode: presetNodes[timelineElementIndex] })
        /* Add node is selected */
        } else if (timelineElementIndex === presetNodes.length) {
            context.commit('CREATE_PRESET_NODE')
        /* End or start of assignment is selected */
        } else {
            const originalAssignment = context.rootGetters['assignment/assignment']
            context.commit('SELECT_ASSIGNMENT_DETAILS', { originalAssignment })
        }
    },

    presetNodeCreated (context, { presetNode }) {
        context.commit('CLEAR_NEW_PRESET_NODE_DRAFT')
        context.commit('SELECT_PRESET_NODE', { presetNode })

        const presetNodes = context.rootGetters['presetNode/assignmentPresetNodes']
        context.commit(
            'SET_TIMELINE_ELEMENT_INDEX',
            { index: presetNodes.findIndex(elem => elem.id === presetNode.id) },
        )
    },

    cancelCategoryEdit (context, { category }) {
        const categories = context.rootGetters['category/assignmentCategories']
        const originalCategory = categories.find(elem => elem.id === category.id)

        context.commit('CLEAR_DRAFT', { drafts: context.state.categoryDrafts, obj: category })
        context.commit('SELECT_CATEGORY', { category: originalCategory })
    },
    cancelPresetNodeEdit (context, { presetNode }) {
        const presetNodes = context.rootGetters['presetNode/assignmentPresetNodes']
        const originalPresetNode = presetNodes.find(elem => elem.id === presetNode.id)

        context.commit('CLEAR_DRAFT', { drafts: context.state.presetNodeDrafts, obj: presetNode })
        context.commit('SELECT_PRESET_NODE', { presetNode: originalPresetNode })
    },
    cancelTemplateEdit (context, { template }) {
        const templates = context.rootGetters['template/assignmentTemplates']
        const originalTemplate = templates.find(elem => elem.id === template.id)

        context.commit('CLEAR_DRAFT', { drafts: context.state.templateDrafts, obj: template })
        context.commit('SELECT_TEMPLATE', { template: originalTemplate })
    },

    confirmIfDirty (context) {
        const dirtyWarnings = []
        const assignment = context.rootGetters['assignment/assignment']
        const categories = context.rootGetters['category/assignmentCategories']
        const presetNodes = context.rootGetters['presetNode/assignmentPresetNodes']
        const templates = context.rootGetters['template/assignmentTemplates']

        if (context.state.assignmentDetailsDraft
            && JSON.stringify(context.state.assignmentDetailsDraft) !== JSON.stringify(assignment)) {
            dirtyWarnings.push('Edit to assignment details.')
        }

        if (context.state.newCategoryDraft) {
            const category = context.state.newCategoryDraft
            dirtyWarnings.push(`New category ${category.name ? `'${category.name}'` : ''} draft.`)
        }
        if (context.state.newPresetNodeDraft) {
            const presetNode = context.state.newPresetNodeDraft
            dirtyWarnings.push(`New deadline ${presetNode.display_name
                ? `'${presetNode.display_name.name}'` : ''} draft.`)
        }
        if (context.state.newTemplateDraft) {
            const template = context.state.newTemplateDraft
            dirtyWarnings.push(`New template ${template.name ? `'${template.name}'` : ''} draft.`)
        }

        Object.values(context.state.categoryDrafts).forEach((draft) => {
            const categoryDraft = draft.draft
            const originalCategory = categories.find(elem => elem.id === categoryDraft.id)

            if (JSON.stringify(originalCategory) !== JSON.stringify(categoryDraft)) {
                dirtyWarnings.push(`Edit to category '${originalCategory.name}'.`)
            }
        })
        Object.values(context.state.presetNodeDrafts).forEach((draft) => {
            const presetNodeDraft = draft.draft
            const originalPresetNode = presetNodes.find(elem => elem.id === presetNodeDraft.id)

            if (JSON.stringify(originalPresetNode) !== JSON.stringify(presetNodeDraft)) {
                dirtyWarnings.push(`Edit to deadline '${originalPresetNode.display_name}'.`)
            }
        })
        Object.values(context.state.templateDrafts).forEach((draft) => {
            const templateDraft = draft.draft
            const originalTemplate = templates.find(elem => elem.id === templateDraft.id)

            if (JSON.stringify(originalTemplate) !== JSON.stringify(templateDraft)) {
                dirtyWarnings.push(`Edit to template '${originalTemplate.name}'.`)
            }
        })

        if (dirtyWarnings.length > 0) {
            return window.confirm(`
The following unsaved changes will be lost:

${dirtyWarnings.map(warn => `- ${warn}\n`)}
Are you sure you want to continue?
            `)
        }

        return true
    },
}

export default {
    namespaced: true,
    state: {
        activeComponentOptions: {
            category: categorySymbol,
            timeline: timelineSymbol,
            template: templateSymbol,
            templateImport: templateImportSymbol,
        },
        activeComponent: timelineSymbol,

        activeComponentModeOptions: {
            read: readSymbol,
            edit: editSymbol,
        },
        activeComponentMode: readSymbol,

        selectedTimelineElementIndex: -1, /* See timeline.vue for mapping (due for refactor). */

        assignmentDetailsDraft: null,

        selectedCategory: null,
        newCategoryDraft: null,
        categoryDrafts: {},

        selectedTemplate: null,
        newTemplateDraft: null,
        templateDrafts: {},

        selectedPresetNode: null,
        newPresetNodeDraft: null,
        presetNodeDrafts: {},
    },
    getters,
    mutations,
    actions,
}
