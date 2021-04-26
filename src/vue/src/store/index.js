import { createStore } from 'vuex-extensions'

import Vue from 'vue'
import Vuex from 'vuex'
import createPersistedState from 'vuex-persistedstate'

import cache from './mixins/cache.js'

import assignment from './modules/assignment.js'
import assignmentEditor from './modules/assignmentEditor.js'
import category from './modules/category.js'
import connection from './modules/connection.js'
import content from './modules/content.js'
import instance from './modules/instance.js'
import permissions from './modules/permissions.js'
import preferences from './modules/preferences.js'
import presetNode from './modules/presetNode.js'
import sentry from './modules/sentry.js'
import template from './modules/template.js'
import timeline from './modules/timeline.js'
import user from './modules/user.js'

Vue.use(Vuex)

const plugins = []

plugins.push(createPersistedState({ paths: ['content', 'permissions', 'preferences', 'user'] }))

export default createStore(Vuex.Store, {
    modules: {
        assignment,
        assignmentEditor,
        category,
        connection,
        content,
        instance,
        permissions,
        preferences,
        presetNode,
        sentry,
        template,
        timeline,
        user,
    },
    mixins: {
        mutations: {
            ...cache.mutations,
        },
        actions: {
            ...cache.actions,
        },
    },
    strict: false,
    plugins,
})
