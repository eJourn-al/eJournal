import Vue from 'vue'
import Vuex from 'vuex'
import createPersistedState from 'vuex-persistedstate'

import assignment from './modules/assignment.js'
import connection from './modules/connection.js'
import content from './modules/content.js'
import permissions from './modules/permissions.js'
import preferences from './modules/preferences.js'
import sentry from './modules/sentry.js'
import user from './modules/user.js'

Vue.use(Vuex)

const debug = process.env.NODE_ENV !== 'production'
const plugins = []

plugins.push(createPersistedState({ paths: ['content', 'permissions', 'preferences', 'user'] }))

export default new Vuex.Store({
    modules: {
        assignment,
        connection,
        content,
        permissions,
        preferences,
        sentry,
        user,
    },
    strict: debug,
    plugins,
})
