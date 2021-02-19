import Vue from 'vue'
import categoryStore from './category.js'
import colorUtils from '@/utils/colors.js'
import presetNodeStore from './presetNode.js'
import templateStore from './template.js'

const categorySymbol = Symbol('category')
const timelineSymbol = Symbol('timeline')
const templateSymbol = Symbol('template')
const templateImportSymbol = Symbol('templateImport')

const readSymbol = Symbol('read')
const editSymbol = Symbol('edit')

function fromDraft (drafts, obj) {
    if (obj.id in drafts) {
        const draft = drafts[obj.id]
        draft.edited = !Vue.prototype.$_isEqual(draft.draft, obj)

        return draft
    }

    const draft = { draft: JSON.parse(JSON.stringify(obj)), edited: false }
    Vue.set(drafts, obj.id, draft)

    return draft
}

function isDraftDirty (drafts, obj) {
    return (obj.id in drafts) ? !Vue.prototype.$_isEqual(drafts[obj.id].draft, obj) : false
}

const getters = {
    activeComponent: (state) => state.activeComponent,
    activeComponentOptions: (state) => state.activeComponentOptions,

    activeComponentMode: (state) => state.activeComponentMode,
    activeComponentModeOptions: (state) => state.activeComponentModeOptions,
    readMode: (state) => state.activeComponentMode === state.activeComponentModeOptions.read,
    editMode: (state) => state.activeComponentMode === state.activeComponentModeOptions.edit,

    assignmentDetailsDraft: (state) => state.assignmentDetailsDraft,

    selectedCategory: (state) => state.selectedCategory,
    newCategoryDraft: (state) => state.newCategoryDraft,

    selectedTemplate: (state) => state.selectedTemplate,
    newTemplateDraft: (state) => state.newTemplateDraft,

    selectedPresetNode: (state) => state.selectedPresetNode,
    newPresetNodeDraft: (state) => state.newPresetNodeDraft,

    selectedTimelineElementIndex: (state) => state.selectedTimelineElementIndex,

    isAssignmentDetailsDirty: (state) => (original) => (
        state.assignmentDetailsDraft && !Vue.prototype.$_isEqual(state.assignmentDetailsDraft, original)
    ),
    isCategoryDirty: (state) => (originalCategory) => isDraftDirty(state.categoryDrafts, originalCategory),
    isPresetNodeDirty: (state) => (originalPresetNode) => isDraftDirty(state.presetNodeDrafts, originalPresetNode),
    isTemplateDirty: (state) => (originalTemplate) => isDraftDirty(state.templateDrafts, originalTemplate),
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
            const edited = !Vue.prototype.$_isEqual(originalAssignment, state.assignmentDetailsDraft)
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
    CREATE_CATEGORY (state, { colorIndex }) {
        if (state.newCategoryDraft) {
            state.selectedCategory = state.newCategoryDraft
        } else {
            const color = colorUtils.getThemeOrRandomColor(colorIndex)

            const newCategory = {
                id: -1,
                name: null,
                description: '',
                color,
                templates: [],
            }

            state.selectedCategory = newCategory
            state.newCategoryDraft = newCategory
        }

        state.activeComponent = state.activeComponentOptions.category
        state.activeComponentMode = state.activeComponentModeOptions.edit
    },
    /* When a category is updated, it is possible its templates were changed.
     * These changes need to be propagated to the the template drafts in order to keep state in sync. */
    PROPAGATE_DRAFT_CATEGORY_TEMPLATE_UPDATE (state, { updatedCategory }) {
        const drafts = Object.values(state.templateDrafts).map((draft) => draft.draft)
        if (state.newTemplateDraft) { drafts.push(state.newTemplateDraft) }

        templateStore.propagateCategoryTemplateUpdate(drafts, updatedCategory)
    },
    /* When a category is deleted, it also needs to be removed from all template drafts */
    PROPAGATE_DRAFT_CATEGORY_DELETE (state, { deletedCategoryId }) {
        const drafts = Object.values(state.templateDrafts).map((draft) => draft.draft)
        if (state.newTemplateDraft) { drafts.push(state.newTemplateDraft) }

        templateStore.propagateCategoryDelete(drafts, deletedCategoryId)
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
    CREATE_TEMPLATE (state, { fromPresetNode }) {
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
                name: '',
                id: -1,
                preset_only: !!fromPresetNode,
                allow_custom_categories: false,
                categories: [],
                fromPresetNode,
            }

            state.selectedTemplate = newTemplate
            state.newTemplateDraft = newTemplate
        }

        state.activeComponent = state.activeComponentOptions.template
        state.activeComponentMode = state.activeComponentModeOptions.edit
    },
    /* When a template is updated, it is possible its categories were changed.
     * These changes need to be propagated to the category drafts in order to keep state in sync. */
    PROPAGATE_DRAFT_TEMPLATE_CATEGORY_UPDATE (state, { updatedTemplate, oldTemplateId }) {
        const drafts = Object.values(state.categoryDrafts).map((draft) => draft.draft)
        if (state.newCategoryDraft) { drafts.push(state.newCategoryDraft) }

        categoryStore.propagateTemplateCategoryUpdate(drafts, updatedTemplate, oldTemplateId)
    },
    /* When a template is deleted, it also needs to be removed from all category drafts */
    PROPAGATE_TEMPLATE_DELETE (state, { deletedTemplateId }) {
        categoryStore.propagateTemplateDelete(
            Object.values(state.categoryDrafts).map((draft) => draft.draft),
            deletedTemplateId,
        )
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
    /* When a template is updated, it is possible preset deadlines' forced template becomes stale.
     * These changes need to be propagated to the preset node drafts in order to keep state in sync. */
    PROPAGATE_DRAFT_TEMPLATE_PRESET_NODE_UPDATE (state, { updatedTemplate, oldTemplateId }) {
        const drafts = Object.values(state.presetNodeDrafts).map((draft) => draft.draft)
        if (state.newPresetNodeDraft) { drafts.push(state.newPresetNodeDraft) }

        presetNodeStore.propagateTemplatePresetNodeUpdate(drafts, updatedTemplate, oldTemplateId)
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
        context.commit('PROPAGATE_DRAFT_CATEGORY_TEMPLATE_UPDATE', { updatedCategory: category })
        context.commit('SELECT_CATEGORY', { category })
    },
    templateCreated (context, { template, fromPresetNode }) {
        context.commit('CLEAR_NEW_TEMPLATE_DRAFT')
        context.commit('PROPAGATE_DRAFT_TEMPLATE_CATEGORY_UPDATE', { updatedTemplate: template })

        if (fromPresetNode) {
            const presetNodes = context.rootGetters['presetNode/assignmentPresetNodes']
            let timelineElementIndex

            if (fromPresetNode.id === -1) {
                timelineElementIndex = presetNodes.length /* Add node should be selected */
            } else {
                timelineElementIndex = presetNodes.findIndex((elem) => elem.id === fromPresetNode.id)
            }

            const presetNodeExists = timelineElementIndex !== -1

            if (presetNodeExists) {
                fromPresetNode.template = template

                context.dispatch(
                    'timelineElementSelected',
                    { timelineElementIndex, mode: context.state.activeComponentModeOptions.edit },
                )
            } else {
                context.commit('SELECT_TEMPLATE', { template })
            }
        } else {
            context.commit('SELECT_TEMPLATE', { template })
        }
    },

    categoryDeleted (context, { category }) {
        context.commit('PROPAGATE_DRAFT_CATEGORY_DELETE', { deletedCategoryId: category.id })

        if (context.state.selectedCategory && context.state.selectedCategory.id === category.id) {
            context.commit('CLEAR_SELECTED_CATEGORY')

            if (context.state.activeComponent === context.state.activeComponentOptions.category) {
                context.commit('CLEAR_ACTIVE_COMPONENT')
            }
        }
    },
    presetNodeDeleted (context, { presetNode }) {
        if (context.state.selectedPresetNode.id === presetNode.id) {
            context.commit('CLEAR_SELECTED_PRESET_NODE')

            if (context.state.activeComponent === context.state.activeComponentOptions.timeline) {
                context.commit('CLEAR_ACTIVE_COMPONENT')
            }
        }
    },
    templateDeleted (context, { template }) {
        context.commit('PROPAGATE_TEMPLATE_DELETE', { deletedTemplateId: template.id })

        if (context.state.selectedTemplate && context.state.selectedTemplate.id === template.id) {
            context.commit('CLEAR_SELECTED_TEMPLATE')

            if (context.state.activeComponent === context.state.activeComponentOptions.template) {
                context.commit('CLEAR_ACTIVE_COMPONENT')
            }
        }
    },

    categoryUpdated (context, { category }) {
        context.commit('CLEAR_DRAFT', { drafts: context.state.categoryDrafts, obj: category })
        context.commit('PROPAGATE_DRAFT_CATEGORY_TEMPLATE_UPDATE', { updatedCategory: category })
        context.commit('SELECT_CATEGORY', { category })
    },
    presetNodeUpdated (context, { presetNode }) {
        context.commit('CLEAR_DRAFT', { drafts: context.state.presetNodeDrafts, obj: presetNode })
        context.commit('SELECT_PRESET_NODE', { presetNode })
    },
    templateUpdated (context, { updatedTemplate, oldTemplateId }) {
        context.commit('CLEAR_DRAFT', { drafts: context.state.templateDrafts, obj: { id: oldTemplateId } })
        context.commit('PROPAGATE_DRAFT_TEMPLATE_CATEGORY_UPDATE', { updatedTemplate, oldTemplateId })
        context.commit('PROPAGATE_DRAFT_TEMPLATE_PRESET_NODE_UPDATE', { updatedTemplate, oldTemplateId })
        context.commit('SELECT_TEMPLATE', { template: updatedTemplate })
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
            { index: presetNodes.findIndex((elem) => elem.id === presetNode.id) },
        )
    },

    cancelCategoryEdit (context, { category }) {
        const categories = context.rootGetters['category/assignmentCategories']
        const originalCategory = categories.find((elem) => elem.id === category.id)

        context.commit('CLEAR_DRAFT', { drafts: context.state.categoryDrafts, obj: category })
        context.commit('SELECT_CATEGORY', { category: originalCategory })
    },
    cancelPresetNodeEdit (context, { presetNode }) {
        const presetNodes = context.rootGetters['presetNode/assignmentPresetNodes']
        const originalPresetNode = presetNodes.find((elem) => elem.id === presetNode.id)

        context.commit('CLEAR_DRAFT', { drafts: context.state.presetNodeDrafts, obj: presetNode })
        context.commit('SELECT_PRESET_NODE', { presetNode: originalPresetNode })
    },
    cancelTemplateEdit (context, { template }) {
        const templates = context.rootGetters['template/assignmentTemplates']
        const originalTemplate = templates.find((elem) => elem.id === template.id)

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
            && !Vue.prototype.$_isEqual(context.state.assignmentDetailsDraft, assignment)) {
            dirtyWarnings.push('Edit to assignment details.')
        }

        if (context.state.newCategoryDraft) {
            const category = context.state.newCategoryDraft
            dirtyWarnings.push(`New category ${category.name ? `'${category.name}' ` : ''}draft.`)
        }
        if (context.state.newPresetNodeDraft) {
            const presetNode = context.state.newPresetNodeDraft
            dirtyWarnings.push(`New deadline ${presetNode.display_name
                ? `'${presetNode.display_name}' ` : ''}draft.`)
        }
        if (context.state.newTemplateDraft) {
            const template = context.state.newTemplateDraft
            dirtyWarnings.push(`New template ${template.name ? `'${template.name}' ` : ''}draft.`)
        }

        Object.values(context.state.categoryDrafts).forEach((draft) => {
            const categoryDraft = draft.draft
            const originalCategory = categories.find((elem) => elem.id === categoryDraft.id)

            if (!Vue.prototype.$_isEqual(originalCategory, categoryDraft)) {
                dirtyWarnings.push(`Edit to category '${originalCategory.name}'.`)
            }
        })
        Object.values(context.state.presetNodeDrafts).forEach((draft) => {
            const presetNodeDraft = draft.draft
            const originalPresetNode = presetNodes.find((elem) => elem.id === presetNodeDraft.id)

            if (!Vue.prototype.$_isEqual(originalPresetNode, presetNodeDraft)) {
                dirtyWarnings.push(`Edit to deadline '${originalPresetNode.display_name}'.`)
            }
        })
        Object.values(context.state.templateDrafts).forEach((draft) => {
            const templateDraft = draft.draft
            const originalTemplate = templates.find((elem) => elem.id === templateDraft.id)

            if (!Vue.prototype.$_isEqual(originalTemplate, templateDraft)) {
                dirtyWarnings.push(`Edit to template '${originalTemplate.name}'.`)
            }
        })

        if (dirtyWarnings.length > 0) {
            return window.confirm(`
The following unsaved changes will be lost:

${dirtyWarnings.map((warn) => `- ${warn}\n`).join('')}
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
