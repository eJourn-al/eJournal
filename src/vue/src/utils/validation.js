import Vue from 'vue'
import genericUtils from '@/utils/generic_utils.js'

export default {
    validatePassword (password, password2) {
        if (password !== password2) {
            Vue.toasted.error('Passwords do not match!')
            return false
        }
        if (password.length < 8) {
            Vue.toasted.error('Password needs to contain at least 8 characters.')
            return false
        }
        if (password.toLowerCase() === password) {
            Vue.toasted.error('Password needs to contain at least 1 capital letter.')
            return false
        }
        const re = /[ !@#$%^&*()_+\-=[\]{};':"\\|,.<>/?]/
        if (!re.test(password)) {
            Vue.toasted.error('Password needs to contain a special character.')
            return false
        }

        return true
    },

    validateEmail (email, displayMessage = true) {
        const re = /^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$/ // eslint-disable-line
        const correctEmail = re.test(String(email).toLowerCase())

        if (displayMessage && !correctEmail) { Vue.toasted.error('The given email address is not valid!') }

        return correctEmail
    },

    validateURL (url, displayMessage = true, checkProtocol = true) {
        const re = /^(?:(?:https?|ftp):\/\/)?(?:(?!(?:10|127)(?:\.\d{1,3}){3})(?!(?:169\.254|192\.168)(?:\.\d{1,3}){2})(?!172\.(?:1[6-9]|2\d|3[0-1])(?:\.\d{1,3}){2})(?:[1-9]\d?|1\d\d|2[01]\d|22[0-3])(?:\.(?:1?\d{1,2}|2[0-4]\d|25[0-5])){2}(?:\.(?:[1-9]\d?|1\d\d|2[0-4]\d|25[0-4]))|(?:(?:[a-z\u00a1-\uffff0-9]-*)*[a-z\u00a1-\uffff0-9]+)(?:\.(?:[a-z\u00a1-\uffff0-9]-*)*[a-z\u00a1-\uffff0-9]+)*(?:\.(?:[a-z\u00a1-\uffff]{2,})))(?::\d{2,5})?(?:\/\S*)?$/ // eslint-disable-line
        const validURL = re.test(url)
        let validProtocol

        if (displayMessage && !validURL) {
            Vue.toasted.error('The given URL is not valid!')
            return validURL
        }

        if (checkProtocol) {
            const protocolRe = /^(http|https|ftp|ftps):\/\/.*/
            validProtocol = protocolRe.test(url)

            if (displayMessage && !validProtocol) {
                Vue.toasted.error('The given URL is not valid, did you include the protocol e.g. http://?')
            }
        }

        return validURL && validProtocol
    },

    validateYouTubeUrlWithVideoID (url) {
        return Boolean(genericUtils.parseYouTubeVideoID(url))
    },
}
