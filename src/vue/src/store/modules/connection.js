import genericUtils from '@/utils/generic_utils.js'
import router from '@/router'
import statuses from '@/utils/constants/status_codes.js'
import * as types from '../constants/mutation-types.js'

function invalidAccessToken (status, error) {
    return status === statuses.UNAUTHORIZED && genericUtils.invalidAccessToken(error)
}

const getters = {
    showConnectionSpinner: state => state.minConTimerRunning || state.openApiCalls > 0,
    fetchingAccessToken: state => state.fetchingAccessToken,
    minConTimerRunning: state => state.minConTimerRunning,
}

const mutations = {
    [types.CLOSE_API_CALL] (state) {
        state.openApiCalls--
    },
    [types.OPEN_API_CALL] (state) {
        state.openApiCalls++
    },
    [types.SET_MIN_CON_TIMER_RUNNING] (state, { val }) {
        state.minConTimerRunning = val
    },
    [types.RETRY_REFRESH_SUBSCRIBERS] (state, data) {
        state.refreshSubscribers.forEach((subscriber) => { subscriber(data.success, data.error) })
    },
    [types.ACCESS_TOKEN_FETCH_COMPLETED] (state) {
        state.fetchingAccessToken = false
    },
    [types.BLOCK_ADDITIONAL_TOKEN_REFRESH_FETCH_ATTEMPTS] (state) {
        state.fetchingAccessToken = true
    },
    [types.CLEAR_REFRESH_SUBSCRIBERS] (state) {
        state.refreshSubscribers = []
    },
    // eslint-disable-next-line object-curly-newline
    [types.PUSH_REFRESH_SUBSCRIBER] (state, { connection, originalRequest, resolve, reject }) {
        state.refreshSubscribers.push((success, retryError) => {
            // eslint-disable-next-line no-unused-expressions
            success ? resolve(connection(originalRequest)) : reject(retryError)
        })
    },
    [types.RESET_CONNECTION] (state) {
        state.openApiCalls = 0
        state.fetchingAccessToken = false
        state.refreshSubscribers = []
        state.minConTimerRunning = false
    },
}

const actions = {
    /* Increments the open request counter, as well as setting a minimal during which the
     * open connection spinner is expected to be shown. */
    handleRequestTracking ({ commit, getters }) { // eslint-disable-line no-shadow
        commit(types.OPEN_API_CALL)
        if (!getters.minConTimerRunning) {
            commit(types.SET_MIN_CON_TIMER_RUNNING, { val: true })
            setTimeout(() => { commit(types.SET_MIN_CON_TIMER_RUNNING, { val: false }) }, 300)
        }
    },
    /* The user has a valid refresh token and the access token is sucessfully updated.
     * Attempt to retry all refresh subscribers and reset state accordingly. */
    handleValidRefreshToken ({ commit }) {
        commit(types.ACCESS_TOKEN_FETCH_COMPLETED)
        commit(types.RETRY_REFRESH_SUBSCRIBERS, { success: true })
        commit(types.CLEAR_REFRESH_SUBSCRIBERS)
    },
    /* The user has an invalid refresh token and possesses no valid tokens.
     * Clear all subscribed function calls, logout the user and redirect to login. */
    handleInvalidRefreshToken ({ commit }) {
        commit(types.ACCESS_TOKEN_FETCH_COMPLETED)
        commit(types.CLEAR_REFRESH_SUBSCRIBERS)
        commit(`user/${types.LOGOUT}`, null, { root: true })
        if (router.app.$route.name !== 'Login') {
            router.push({ name: 'Login' })
        }
        router.app.$toasted.error('Please login.')
    },
    /* Queues all requests which fail due to an invalid access token.
     * Performs a single access token refresh requests on encountering such a failure.
     * - On success all queued request are repeated.
     * - On failure all queued request are failed silently, and the user is redirected to login. */
    setupTokenRefreshErrorInterceptor ({ commit, getters, dispatch }, { connection }) { // eslint-disable-line no-shadow
        connection.interceptors.response.use(null, (error) => {
            if (error.response === undefined) {
                return Promise.reject(error)
            }
            const { config, response: { status } } = error
            const originalRequest = config

            if (invalidAccessToken(status, error)) {
                if (!getters.fetchingAccessToken) {
                    commit(types.BLOCK_ADDITIONAL_TOKEN_REFRESH_FETCH_ATTEMPTS)
                    dispatch('user/validateToken', null, { root: true }).then(() => {
                        dispatch('handleValidRefreshToken')
                    }, () => {
                        dispatch('handleInvalidRefreshToken')
                    })
                }

                const retryOriginalRequest = new Promise((resolve, reject) => {
                    // eslint-disable-next-line object-curly-newline
                    commit(types.PUSH_REFRESH_SUBSCRIBER, { connection, originalRequest, resolve, reject })
                })

                return retryOriginalRequest
            } else {
                return Promise.reject(error)
            }
        })
    },
    /* The 'connection counter' interceptors should be moved to global, however they are not copied over to
     * instance handlers see:
     * https://github.com/axios/axios/issues/1226 */
    setupDefaultConnectionInterceptors ({ commit }, { connection }) {
        connection.interceptors.request.use((config) => {
            /* Handle anything before the request is sent */
            commit(types.OPEN_API_CALL)
            return config
        }, (error) => {
            /* Handle anything when the request errors. */
            commit(types.CLOSE_API_CALL)
            return Promise.reject(error)
        })

        connection.interceptors.response.use((response) => {
            /* Do anything with the response before further handling. */
            commit(types.CLOSE_API_CALL)
            return response
        }, (error) => {
            /* Do anything with the response error before further handling. */
            commit(types.CLOSE_API_CALL)
            return Promise.reject(error)
        })
    },
    setupConnectionInterceptors ({ dispatch }, { connection, isRefresh = false }) {
        dispatch('setupDefaultConnectionInterceptors', { connection })
        if (!isRefresh) {
            dispatch('setupTokenRefreshErrorInterceptor', { connection })
        }
    },
}

export default {
    namespaced: true,
    state: {
        openApiCalls: 0,
        fetchingAccessToken: false,
        refreshSubscribers: [],
        minConTimerRunning: false,
    },
    getters,
    mutations,
    actions,
}
