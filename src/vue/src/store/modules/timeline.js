import Vue from 'vue'


const getters = {
    filteredCategories: state => state.filteredCategories,
    timelineInstance: state => state.timelineInstance,
}

const mutations = {
    SET_FILTERED_CATEGORIES (state, filteredCategories) {
        state.filteredCategories = filteredCategories
    },
    REMOVE_CATEGORY_FROM_FILTER (state, { id }) {
        Vue.delete(state.filteredCategories, state.filteredCategories.findIndex(elem => elem.id === id))
    },
    CLEAR_FILTERED_CATEGORIES (state) {
        state.filteredCategories = []
    },
    SET_TIMELINE_INSTANCE (state, instance) {
        state.timelineInstance = instance
    },
}

export default {
    namespaced: true,
    state: {
        filteredCategories: [], /* Filter used for the timeline */
        timelineInstance: null,
    },
    getters,
    mutations,
}
