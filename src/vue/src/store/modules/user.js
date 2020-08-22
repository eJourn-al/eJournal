import Vue from 'vue'
import connection from '@/api/connection.js'
import genericUtils from '@/utils/generic_utils.js'
import sanitization from '@/utils/sanitization.js'
import * as types from '../constants/mutation-types.js'

const getters = {
    jwtAccess: state => state.jwtAccess,
    jwtRefresh: state => state.jwtRefresh,
    uID: state => state.uID,
    username: state => state.username,
    email: state => state.email,
    verifiedEmail: state => state.verifiedEmail,
    profilePicture: state => state.profilePicture,
    fullName: state => state.fullName,
    ltiID: state => state.ltiID,
    permissions: state => state.permissions,
    isTestStudent: state => state.is_test_student,
    isSuperuser: state => state.isSuperuser,
    // We are not logged unless the store is populated as well
    loggedIn: state => state.jwtAccess !== null && state.uID !== null,
    storePopulated: state => state.uID !== null,
}

const mutations = {
    [types.SET_ACCES_TOKEN] (state, accessToken) {
        state.jwtAccess = accessToken
    },
    [types.SET_JWT] (state, data) {
        const access = data.access
        const refresh = data.refresh

        state.jwtAccess = access
        state.jwtRefresh = refresh
    },
    [types.HYDRATE_USER] (state, data) {
        const userData = data.user
        const permissions = data.user.permissions

        state.uID = userData.id
        state.username = userData.username
        state.email = userData.email
        state.verifiedEmail = userData.verified_email
        state.profilePicture = userData.profile_picture
        state.fullName = userData.full_name
        state.ltiID = userData.lti_id
        state.isSuperuser = userData.is_superuser
        state.permissions = permissions
    },
    [types.LOGOUT] (state) {
        state.jwtAccess = null
        state.jwtRefresh = null
        state.uID = null
        state.username = null
        state.email = null
        state.verifiedEmail = null
        state.profilePicture = null
        state.fullName = null
        state.ltiID = null
        state.permissions = null
        state.isTestStudent = null
    },
    [types.EMAIL_VERIFIED] (state) {
        state.verifiedEmail = true
    },
    [types.SET_EMAIL] (state, val) {
        state.email = val
    },
    [types.SET_FULL_USER_NAME] (state, data) {
        state.fullName = data.fullName
    },
    [types.SET_PROFILE_PICTURE] (state, dataURL) {
        state.profilePicture = dataURL
    },
    [types.UPDATE_PERMISSIONS] (state, data) {
        const permissions = data.permissions
        const permissionKey = data.key

        state.permissions[permissionKey] = permissions
    },
    [types.IMPORT_ASSIGNMENT_PERMISSIONS] (state, data) {
        const importAssignmentID = data.importAssignmentID
        const sourceAssignmentID = data.sourceAssignmentID
        const permissionImport = JSON.parse(JSON.stringify(state.permissions[`assignment${sourceAssignmentID}`]))

        state.permissions[`assignment${importAssignmentID}`] = permissionImport
    },
}

const actions = {
    /* Authenticates the user and poplates the store, if either fails the login fails. */
    login ({ state, commit, dispatch }, { username, password }) {
        return new Promise((resolve, reject) => {
            connection.conn.post('/token/', { username, password }).then((response) => {
                commit(types.SET_JWT, response.data)

                dispatch('populateStore').then(() => {
                    commit(`sentry/${types.SET_SENTRY_USER_SCOPE}`, { uID: state.uID }, { root: true })
                    resolve('JWT and store are set successfully.')
                }, (error) => {
                    Vue.toasted.error(sanitization.escapeHtml(error.response.data.description))
                    reject(error) // Login success but hydration failed
                })
            }, (error) => {
                reject(error) // Login failed, hydration failed.
            })
        })
    },
    logout ({ commit }) {
        return Promise.all([
            commit(`content/${types.RESET_CONTENT}`, null, { root: true }),
            commit(`preferences/${types.RESET_PREFERENCES}`, null, { root: true }),
            commit(`permissions/${types.RESET_PERMISSIONS}`, null, { root: true }),
            commit(`connection/${types.RESET_CONNECTION}`, null, { root: true }),
            commit(types.LOGOUT),
        ])
    },
    /* An attempt is made at refreshing the JW access token, store is populated if needed.
     * Fails if the refresh fails or if the store needed to be populated if that fails as well. */
    validateToken ({ commit, dispatch, getters }, error = null) { // eslint-disable-line
        let code

        if (error) {
            if (error.response.data instanceof ArrayBuffer) {
                code = genericUtils.parseArrayBuffer(error.response.data).code
            } else {
                code = error.response.data.code
            }
        }

        return new Promise((resolve, reject) => {
            if (!error || code === 'token_not_valid') {
                connection.connRefresh.post('token/refresh/', { refresh: getters.jwtRefresh }).then((response) => {
                    commit(types.SET_ACCES_TOKEN, response.data.access) // Refresh token valid, update access token.

                    if (!getters.storePopulated) {
                        dispatch('populateStore')
                            .then(() => { resolve() })
                            .catch((populateError) => { reject(populateError) })
                    } else {
                        resolve('JWT refreshed successfully, store was already populated.')
                    }
                }, (invalidRefreshTokenError) => {
                    reject(invalidRefreshTokenError)
                })
            } else {
                reject(error) // We should not validate if the error has nothing to do with the token
            }
        })
    },
    populateStore ({ commit }) {
        return new Promise((resolve, reject) => {
            connection.conn.get('/users/0/').then((response) => {
                commit(types.HYDRATE_USER, response.data)
                connection.conn.get(`/preferences/${response.data.user.id}/`).then((preferencesResponse) => {
                    commit(`preferences/${types.HYDRATE_PREFERENCES}`, preferencesResponse.data.preferences,
                        { root: true })
                    resolve('Store is populated successfully')
                }, (error) => {
                    Vue.toasted.error(
                        `Error loading preferences: ${sanitization.escapeHtml(error.response.data.description)}`)
                    reject(error)
                })
            }, (error) => {
                Vue.toasted.error(`Error logging in: ${sanitization.escapeHtml(error.response.data.description)}`)
                reject(error)
            })
        })
    },
}

export default {
    namespaced: true,
    state: {
        jwtAccess: null,
        jwtRefresh: null,
        uID: null,
        username: null,
        email: null,
        verifiedEmail: false,
        isTestStudent: null,
        profilePicture: null,
        fullName: null,
        ltiID: null,
        permissions: null,
        isSuperuser: false,
    },
    getters,
    mutations,
    actions,
}
