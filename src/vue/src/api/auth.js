import axios from 'axios'
import connection from '@/api/connection.js'
import genericUtils from '@/utils/generic_utils.js'
import router from '@/router/index.js'
import sanitization from '@/utils/sanitization.js'
import statuses from '@/utils/constants/status_codes.js'
import store from '@/store/index.js'

const ERRORS_TO_REDIRECT = new Set([
    statuses.FORBIDDEN,
    statuses.NOT_FOUND,
    statuses.INTERNAL_SERVER_ERROR,
])

const TOKEN_INVALID_MSG = 'Given token not valid for any token type'

/*
 * Defines how success and error responses are handled and toasted by default.
 *
 * Changes can be made by overwriting the DEFAULT_CONN_ARGS keys in an API call.
 * Handled errors are redirected by default when present in ERRORS_TO_REDIRECT unless redirect set to false.
 * Handled errors messages default to: response.data.description, unless customErrorToast set.
 * Handled successes do not redirect or display a message unless:
 *    - responseSuccessToast set, toasting the response description
 *    - customSuccessToast is set, toasting the given message.
 */
const DEFAULT_CONN_ARGS = {
    redirect: true,
    customSuccessToast: false,
    responseSuccessToast: false,
    customErrorToast: false,
}

/* Sets default connection arguments to missing keys, otherwise use the given connArgs value. */
function packConnArgs (connArgs) {
    if (!(connArgs instanceof Object) || Object.keys(connArgs).length === 0) {
        throw Error('Connection arguments should be a non emtpy object.')
    }

    Object.keys(connArgs).forEach((key) => {
        if (!(key in DEFAULT_CONN_ARGS)) { throw Error(`Unknown connection argument key: ${key}`) }
    })

    return { ...DEFAULT_CONN_ARGS, ...connArgs }
}

/* Toasts an error safely, escaping html and parsing an array buffer. */
function toastError (error, connArgs) {
    if (connArgs.customErrorToast) {
        router.app.$toasted.error(sanitization.escapeHtml(connArgs.customErrorToast))
    } else if (connArgs.customErrorToast !== '') {
        let data
        if (error.response.data instanceof ArrayBuffer) {
            data = genericUtils.parseArrayBuffer(error.response.data)
        } else {
            data = error.response.data
        }

        /* The Django throttle module uses detail as description. */
        const message = data.description ? data.description : data.detail
        if (message && message !== TOKEN_INVALID_MSG) {
            router.app.$toasted.error(sanitization.escapeHtml(message))
        }
    }
}

/* Lowers the connection count and toast a success message
 * if a custom one is provided or responseSuccessToast is set. */
function handleSuccess (resp, connArgs) {
    if (connArgs.responseSuccessToast) {
        let message
        if (resp.data instanceof ArrayBuffer) {
            message = genericUtils.parseArrayBuffer(resp.data).description
        } else {
            message = resp.data.description
        }

        if (message) { router.app.$toasted.success(sanitization.escapeHtml(message)) }
    } else if (connArgs.customSuccessToast) {
        router.app.$toasted.success(sanitization.escapeHtml(connArgs.customSuccessToast))
    }

    return resp
}

/*
 * Redirects the following unsuccessful request responses:
 * UNAUTHORIZED to Login, logs the client out and clears store.
 * FORBIDDEN, NOT_FOUND, INTERNAL_SERVER_ERROR to Error page.
 *
 * The response is thrown and further promise handling should take place.
 * This because this is generic response handling, and we dont know what should happen in case of an error.
 */
function handleError (error, connArgs) {
    if (error.response === undefined) {
        throw error
    }
    const response = error.response
    const status = response.status

    if (connArgs.redirect && status === statuses.UNAUTHORIZED && router.app.$route.name !== 'Login') {
        store.commit('user/LOGOUT')
        router.push({ name: 'Login' })
        toastError(error, connArgs)
    } else if (connArgs.redirect && ERRORS_TO_REDIRECT.has(status) && router.app.$route.name !== 'ErrorPage') {
        router.push({
            name: 'ErrorPage',
            params: {
                code: status,
                reasonPhrase: response.statusText,
                description: response.data.description,
            },
        })
    } else if (router.app.$route.name !== 'ErrorPage' && (!connArgs.redirect || !ERRORS_TO_REDIRECT.has(status))) {
        // If page is not the error page, nor requires a redirect, display toast
        toastError(error, connArgs)
    }

    throw error
}

function initRequest (func, url, data = null, connArgs = DEFAULT_CONN_ARGS) {
    const packedConnArgs = packConnArgs(connArgs)

    // for a list of the executed Axios aliases see: https://github.com/axios/axios#request-method-aliases
    // NOTE: paramater 'data' can also function as 'config' depending on which alias is used.
    return func(url, data).then(
        (resp) => handleSuccess(resp, packedConnArgs),
        (error) => handleError(error, packedConnArgs))
}

function improveUrl (url, data = null) {
    let improvedUrl = url
    if (improvedUrl[0] !== '/') { improvedUrl = `/${improvedUrl}` }
    if (improvedUrl.slice(-1) !== '/' && !improvedUrl.includes('?')) { improvedUrl += '/' }
    if (data) {
        improvedUrl += '?'
        Object.keys(data).forEach((key) => { improvedUrl += `${key}=${encodeURIComponent(data[key])}&` })
        improvedUrl = improvedUrl.slice(0, -1)
    }

    return improvedUrl
}
/*
 * Previous functions are 'private', following are 'public'.
 */
export default {
    DEFAULT_CONN_ARGS,

    /* Create a user and add it to the database. */
    register (username, password, fullName, email, launchId = null, connArgs = DEFAULT_CONN_ARGS) {
        return initRequest(connection.conn.post, improveUrl('users'), {
            username,
            password,
            full_name: fullName,
            email,
            launch_id: launchId,
        }, connArgs)
            .then((response) => response.data.user)
    },

    /* Change password (old password is known by user). */
    changePassword (newPassword, oldPassword, connArgs = DEFAULT_CONN_ARGS) {
        return this.update('users/password', { new_password: newPassword, old_password: oldPassword }, connArgs)
    },

    /* Forgot password.
     * Checks if a user is known by the given email or username. Sends an email with a link to reset the password. */
    forgotPassword (identifier, connArgs = DEFAULT_CONN_ARGS) {
        return initRequest(connection.conn.post, improveUrl('forgot_password'), { identifier }, connArgs)
    },

    /* Recover password (old password is not known by user, token is used). */
    setPassword (username, token, newPassword, connArgs = DEFAULT_CONN_ARGS) {
        return initRequest(connection.conn.post, improveUrl('recover_password'), {
            username,
            token,
            new_password: newPassword,
        }, connArgs)
    },

    get (url, data, connArgs) {
        return initRequest(connection.conn.get, improveUrl(url, data), null, connArgs)
    },
    post (url, data, connArgs) {
        return initRequest(connection.conn.post, improveUrl(url), data, connArgs)
    },
    patch (url, data, connArgs) {
        return initRequest(connection.conn.patch, improveUrl(url), data, connArgs)
    },
    delete (url, data, connArgs) {
        return initRequest(connection.conn.delete, improveUrl(url, data), null, connArgs)
    },
    /* Each upload request can be accompanied by a custom 'onUploadProgress' handler, which is why a dedicated instance
     * is created for each request. */
    uploadFile (url, data, config, connArgs) {
        const axiosInstance = axios.create({
            headers: {
                'Content-Type': 'multipart/form-data',
            },
            ...config,
        })
        store.dispatch('connection/setupConnectionInterceptors', { connection: axiosInstance })

        return initRequest(axiosInstance.post, improveUrl(url), data, connArgs)
    },
    downloadFile (url, data, connArgs) {
        return initRequest(connection.connDownFile.get, improveUrl(url, data), null, connArgs)
    },
    create (url, data, connArgs) { return this.post(url, data, connArgs) },
    update (url, data, connArgs) { return this.patch(url, data, connArgs) },
}
