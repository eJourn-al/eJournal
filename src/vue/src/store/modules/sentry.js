import * as Sentry from '@sentry/browser'
import * as types from '../constants/mutation-types.js'

const getters = {
    lastEvenID: (state) => state.lastEvenID,
}

const mutations = {
    [types.SET_LAST_EVENT_ID] (state, { eventID }) {
        state.lastEvenID = eventID
    },
    [types.SET_SENTRY_USER_SCOPE] (_, data) {
        Sentry.configureScope((scope) => {
            scope.setUser(data)
        })
    },
    [types.RESET_SENTRY] (state) {
        state.lastEvenID = null
        Sentry.configureScope((scope) => {
            scope.clear()
        })
    },
    [types.CAPTURE_SCOPED_MESSAGE] (_, data) {
        const msg = 'msg' in data ? data.msg : ''
        const extra = 'extra' in data ? data.extra : {}
        const tags = 'tags' in data ? data.tags : {}
        const level = 'level' in data ? data.level : 'error'

        Sentry.withScope((scope) => {
            for (const [key, value] of Object.entries(extra)) { /* eslint-disable-line */
                scope.setExtra(key, value)
            }
            for (const [key, value] of Object.entries(tags)) { /* eslint-disable-line */
                scope.setTag(key, value)
            }
            scope.setLevel(level)
            /* User data is appended in the before send */
            Sentry.captureMessage(msg)
        })
    },
}

export default {
    namespaced: true,
    state: {
        lastEvenID: null,
    },
    getters,
    mutations,
}
