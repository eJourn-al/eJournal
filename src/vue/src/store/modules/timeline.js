import Vue from 'vue'

const startNodeSymbol = 's'
const addNodeSymbol = 'a'
const endNodeSymbol = 'n'

const getters = {
    startNodeSymbol: (state) => state.startNodeSymbol,
    addNodeSymbol: (state) => state.addNodeSymbol,
    endNodeSymbol: (state) => state.endNodeSymbol,

    startNode: (state) => state.startNode,
    addNode: (state) => state.addNode,
    endNode: (state) => state.endNode,

    filteredCategories: (state) => state.filteredCategories,
    filteringCategoriesForAssignmentId: (state) => state.filteringCategoriesForAssignmentId,
    timelineInstance: (state) => state.timelineInstance,
    currentNode: (state) => state.currentNode,
}

const mutations = {
    SET_FILTERED_CATEGORIES (state, filteredCategories) {
        state.filteredCategories = filteredCategories
        state.filteringCategoriesForAssignmentId = parseInt(this.state.route.params.aID, 10)
    },
    REMOVE_CATEGORY_FROM_FILTER (state, { id }) {
        Vue.delete(state.filteredCategories, state.filteredCategories.findIndex((elem) => elem.id === id))
    },
    CLEAR_FILTERED_CATEGORIES (state) {
        state.filteredCategories = []
    },
    SET_TIMELINE_INSTANCE (state, instance) {
        state.timelineInstance = instance
    },
    SET_CURRENT_NODE (state, node) {
        if (state.nodeNavigationGuards.every((guard) => guard())) {
            state.currentNode = node
        }
    },
    PUSH_NODE_NAVIGATION_GUARD (state, fn) {
        state.nodeNavigationGuards.push(fn)
    },
    REMOVE_NODE_NAVIGATION_GUARD (state, fn) {
        state.nodeNavigationGuards = state.nodeNavigationGuards.filter((guard) => guard !== fn)
    },
}

export default {
    namespaced: true,
    state: {
        startNodeSymbol,
        addNodeSymbol,
        endNodeSymbol,

        startNode: { type: startNodeSymbol },
        addNode: { type: addNodeSymbol },
        endNode: { type: endNodeSymbol },

        filteredCategories: [], /* Filter used for the timeline */
        filteringCategoriesForAssignmentId: null,
        timelineInstance: null,
        currentNode: null,

        nodeNavigationGuards: [],
    },
    getters,
    mutations,
}
