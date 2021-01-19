const timelineSymbol = Symbol('timeline')
const templateSymbol = Symbol('template')
const templateImportSymbol = Symbol('templateImport')

const readSymbol = Symbol('read')
const editSymbol = Symbol('edit')

const getters = {
    activeComponentOptions: state => state.activeComponentOptions,
    activeComponent: state => state.activeComponent,
    activeComponentModeOptions: state => state.activeComponentModeOptions,
    activeComponentMode: state => state.activeComponentMode,
    selectedTemplate: state => state.selectedTemplate,
    templateDraft: state => state.templateDraft,
}

const mutations = {
    setActiveComponent (state, componentSymbol) {
        state.activeComponent = componentSymbol
    },
    setActiveComponentMode (state, modeSymbol) {
        state.activeComponentMode = modeSymbol
    },
    setActiveComponentModeToRead (state) {
        state.activeComponentMode = state.activeComponentModeOptions.read
    },
    selectTemplate (state, { template, mode = editSymbol }) {
        state.selectedTemplate = template
        state.activeComponent = state.activeComponentOptions.template
        state.activeComponentMode = mode
    },
    createTemplate (state, { template }) {
        state.selectedTemplate = template
        state.templateDraft = template
        state.activeComponent = state.activeComponentOptions.template
        state.activeComponentMode = state.activeComponentModeOptions.edit
    },
    templateCreated (state) {
        state.templateDraft = null
        state.activeComponentMode = state.activeComponentModeOptions.read
    },
    clearSelectedTemplate (state) {
        state.selectedTemplate = null
    },
    clearActiveComponent (state) {
        state.activeComponentMode = state.activeComponentModeOptions.read
        state.activeComponent = state.activeComponentOptions.timeline
    },
}

const actions = {
    templateDeleted (context, template) {
        if (
            context.state.activeComponent === context.state.activeComponentOptions.template
            && context.state.selectedTemplate === template
        ) {
            context.commit('clearActiveComponent')
            context.commit('clearSelectedTemplate')
        }
    },
}

export default {
    namespaced: true,
    state: {
        activeComponentOptions: {
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
        selectedTemplate: null, /* TODO: Would a more generic type be preferred, e.g. activeComponentData */
        templateDraft: null,
    },
    getters,
    mutations,
    actions,
}
