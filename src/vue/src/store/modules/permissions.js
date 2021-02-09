import * as mutationTypes from '../constants/mutation-types.js'
import * as types from '../constants/permission-types.js'
import Vue from 'vue'
import connection from '@/api/connection.js'
import router from '@/router/index.js'
import store from '@/store/index.js'

/* If no update has been performed in the last thirty seconds, update permissions */
function canRefreshPermissions () {
    if (!store.getters['user/storePopulated']) { return false }

    const thirtySecs = 30 * 1000
    const date = new Date()
    return (!store.getters['permissions/lastPermissionUpdate']
            || ((date - new Date(store.getters['permissions/lastPermissionUpdate'])) > thirtySecs))
}

/* Attempt to update the permissions, throw error if this cannot be done and is not underway. */
function handleError (error = null) {
    if (canRefreshPermissions()) {
        store.dispatch('permissions/updatePermissions')
    } else if (error && !store.getters['permissions/permissionUpdateInFlight']) {
        throw error
    }
}

function getPermission (permissions, levelAndID, permission) {
    if (levelAndID in permissions && permission in permissions[levelAndID]) {
        return permissions[levelAndID][permission]
    }

    /* Unknown permission combination. */
    handleError(null)

    return false
}

const getters = {
    lastPermissionUpdate: state => state.lastPermissionUpdate,
    permissionUpdateInFlight: state => state.permissionUpdateInFlight,
    // eslint-disable-next-line
    hasPermission: (state, getters, rootState, rootGetters) => (permission, givenKeyLevel = null, id = null) => {
        if (!rootGetters['user/loggedIn']) { return false }
        if (rootGetters['user/isSuperuser']) { return permission !== 'can_have_journal' }
        if ((!types.ALL_PERIMSSIONS.has(permission))) {
            throw Error(`Permission input error, the requested permission: ${permission} does not exist.`)
        }
        if (givenKeyLevel && !types.PERMISSION_KEY_LEVELS.has(givenKeyLevel)) {
            throw Error('Permission input error, the requested key level does not exist.')
        }
        if (givenKeyLevel === 'general' && id) {
            throw Error('Permission input error, general permissions are without id.')
        }

        const permissions = rootGetters['user/permissions']
        const routeParams = router.currentRoute.params

        if (givenKeyLevel && id) {
            if (permissions[givenKeyLevel + id] === undefined) {
                handleError(Error(`Permission type input error, no match for the given key: ${givenKeyLevel}${id}.`))
            }
            if (permissions[givenKeyLevel + id] && permissions[givenKeyLevel + id][permission] === undefined) {
                handleError(Error(
                    `Permission ${permission} is not a valid permission for the context: ${givenKeyLevel}${id}.`))
            }
            return getPermission(permissions, `${givenKeyLevel}${id}`, permission)
        } else if (givenKeyLevel) {
            return getPermission(permissions, givenKeyLevel, permission)
        } else if ('cID' in routeParams && types.COURSE_LEVEL_PERMISSIONS.has(permission)) {
            return getPermission(permissions, `course${routeParams.cID}`, permission)
        } else if ('aID' in routeParams && types.ASSIGNMENT_LEVEL_PERMISSIONS.has(permission)) {
            return getPermission(permissions, `assignment${routeParams.aID}`, permission)
        } else if (types.GENERAL_LEVEL_PERMISSIONS.has(permission)) {
            return getPermission(permissions, 'general', permission)
        } else {
            throw Error(`Permission ${permission} is not a valid permission for the context: {course${routeParams.cID},
                        assignment${routeParams.aID}, general}.`)
        }
    },
}

const mutations = {
    [mutationTypes.SET_LAST_PERMISSION_UPDATE] (state, { date }) {
        state.lastPermissionUpdate = date
    },
    [mutationTypes.SET_PERMISSION_UPDATE_IN_FLIGHT] (state, { val }) {
        state.permissionUpdateInFlight = val
    },
    [mutationTypes.RESET_PERMISSIONS] (state) {
        state.lastPermissionUpdate = null
        state.permissionUpdateInFlight = false
    },
}

const actions = {
    /* Update the permissions, keeping track of the request flight status and setting a cooldown timer.
     * Triggers a global update if the permissions have in fact changed to the clients previous state. */
    updatePermissions ({ commit, rootGetters }) {
        const permissionsCopy = JSON.parse(JSON.stringify(rootGetters['user/permissions']))

        commit(mutationTypes.SET_LAST_PERMISSION_UPDATE, { date: new Date() })
        commit(mutationTypes.SET_PERMISSION_UPDATE_IN_FLIGHT, { val: true })

        connection.conn.get('/users/0/').then((response) => {
            commit(`user/${mutationTypes.HYDRATE_USER}`, response.data, { root: true })
            commit(mutationTypes.SET_PERMISSION_UPDATE_IN_FLIGHT, { val: false })
            if (!Vue.prototype.$_isEqual(permissionsCopy, rootGetters['user/permissions'])) {
                Vue.forceUpdate()
            }
        }).catch(() => {
            commit(mutationTypes.SET_PERMISSION_UPDATE_IN_FLIGHT, { val: false })
        })
    },
}

export default {
    namespaced: true,
    getters,
    mutations,
    actions,
    state: {
        lastPermissionUpdate: null,
        permissionUpdateInFlight: false,
    },
}
