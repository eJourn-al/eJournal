import Vue from 'vue'
import Vuex from 'vuex'
import createPersistedState from 'vuex-persistedstate'

import assignment from './modules/assignment.js'
import assignmentEditor from './modules/assignmentEditor.js'
import category from './modules/category.js'
import connection from './modules/connection.js'
import content from './modules/content.js'
import permissions from './modules/permissions.js'
import preferences from './modules/preferences.js'
import presetNode from './modules/presetNode.js'
import sentry from './modules/sentry.js'
import template from './modules/template.js'
import user from './modules/user.js'

Vue.use(Vuex)

const plugins = []

plugins.push(createPersistedState({ paths: ['content', 'permissions', 'preferences', 'user'] }))

export default new Vuex.Store({
    modules: {
        assignment,
        assignmentEditor,
        category,
        connection,
        content,
        permissions,
        preferences,
        presetNode,
        sentry,
        template,
        user,
    },
    strict: false,
    plugins,
})
