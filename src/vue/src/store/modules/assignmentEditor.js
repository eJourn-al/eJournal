import colorUtils from '@/utils/colors.js'

const categorySymbol = Symbol('category')
const timelineSymbol = Symbol('timeline')
const templateSymbol = Symbol('template')
const templateImportSymbol = Symbol('templateImport')

const readSymbol = Symbol('read')
const editSymbol = Symbol('edit')

const getters = {
    activeComponent: state => state.activeComponent,
    activeComponentOptions: state => state.activeComponentOptions,

    activeComponentMode: state => state.activeComponentMode,
    activeComponentModeOptions: state => state.activeComponentModeOptions,
    readMode: state => state.activeComponentMode === state.activeComponentModeOptions.read,
    editMode: state => state.activeComponentMode === state.activeComponentModeOptions.edit,

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

    SELECT_CATEGORY (state, { category, mode = readSymbol }) {
        state.selectedCategory = category
        state.activeComponent = state.activeComponentOptions.category
        state.activeComponentMode = mode
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
    CATEGORY_CREATED (state, { category }) {
        state.newCategoryDraft = null
        state.selectedCategory = category
        state.activeComponent = state.activeComponentOptions.category
        state.activeComponentMode = state.activeComponentModeOptions.read
    },

    SELECT_TEMPLATE (state, { template, mode = readSymbol }) {
        state.selectedTemplate = template
        state.activeComponent = state.activeComponentOptions.template
        state.activeComponentMode = mode
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
    TEMPLATE_CREATED (state, { template }) {
        state.newTemplateDraft = null
        state.selectedTemplate = template
        state.activeComponent = state.activeComponentOptions.template
        state.activeComponentMode = state.activeComponentModeOptions.read
    },
    SET_ACTIVE_COMPONENT_TO_TEMPLATE_IMPORT (state) {
        state.activeComponent = state.activeComponentOptions.templateImport
    },
    CLEAR_SELECTED_TEMPLATE (state) {
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
    SET_SELECTED_PRESET_NODE (state, { presetNode }) {
        state.selectedPresetNode = presetNode
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
    PRESET_NODE_SELECTED (state, { presetNode }) {
        state.selectedPresetNode = presetNode
    },
    CLEAR_PRESET_NODE_DRAFT (state) {
        state.newPresetNodeDraft = null
    },

    CLEAR_ACTIVE_COMPONENT (state) {
        state.activeComponentMode = state.activeComponentModeOptions.read
        state.activeComponent = state.activeComponentOptions.timeline
    },

    RESET (state) {
        state.selectedTimelineElementIndex = -1

        state.selectedCategory = null
        state.newCategoryDraft = null

        state.selectedTemplate = null
        state.newTemplateDraft = null

        state.selectedPresetNode = null
        state.newPresetNodeDraft = null
    },
}

const actions = {
    templateDeleted (context, template) {
        if (
            context.state.activeComponent === context.state.activeComponentOptions.template
            && context.state.selectedTemplate === template
        ) {
            context.commit('CLEAR_ACTIVE_COMPONENT')
            context.commit('CLEAR_SELECTED_TEMPLATE')
        }
    },
    timelineElementSelected (context, { timelineElementIndex, mode = editSymbol }) {
        context.commit('SELECT_TIMELINE_ELEMENT', { timelineElementIndex, mode })

        const presetNodes = context.rootGetters['presetNode/assignmentPresetNodes']

        /* Actual preset node selected */
        if (timelineElementIndex >= 0 && timelineElementIndex < presetNodes.length) {
            context.commit('PRESET_NODE_SELECTED', { presetNode: presetNodes[timelineElementIndex] })
        /* Add node is selected */
        } else if (timelineElementIndex === presetNodes.length) {
            context.commit('CREATE_PRESET_NODE')
        }
    },
    presetNodeCreated (context, { presetNode }) {
        context.commit('CLEAR_PRESET_NODE_DRAFT')
        context.commit('SET_SELECTED_PRESET_NODE', { presetNode })
        context.commit('SET_ACTIVE_COMPONENT_MODE_TO_READ')

        const presetNodes = context.rootGetters['presetNode/assignmentPresetNodes']
        context.commit(
            'SET_TIMELINE_ELEMENT_INDEX',
            { index: presetNodes.findIndex(elem => elem.id === presetNode.id) },
        )
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

        selectedCategory: null,
        newCategoryDraft: null,

        selectedTemplate: null,
        newTemplateDraft: null,

        selectedPresetNode: null,
        newPresetNodeDraft: null,
    },
    getters,
    mutations,
    actions,
}
