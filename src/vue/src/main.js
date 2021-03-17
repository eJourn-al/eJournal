import 'flatpickr/dist/flatpickr.css' // eslint-disable-line import/no-extraneous-dependencies
import 'flatpickr/dist/themes/material_blue.css' // eslint-disable-line import/no-extraneous-dependencies
import 'intro.js/introjs.css' // eslint-disable-line import/no-extraneous-dependencies
import Vue from 'vue'
import isEqualWith from 'lodash.isequalwith'

import '@/helpers/vue_awesome_icons.js'
import initBootstrap from '@/helpers/bootstrap.js'
import initGlobalHelpers from '@/helpers/global_mixins.js'
import initSentry from '@/helpers/sentry.js'

import Icon from 'vue-awesome/components/Icon.vue'
import Toasted from 'vue-toasted'
import VueIntro from 'vue-introjs'
import flatPickr from 'vue-flatpickr-component'

import connection from '@/api/connection.js'

import { sync } from 'vuex-router-sync'

import App from './App.vue'
import ResetWrapper from '@/components/assets/ResetWrapper.vue'
import ThemeSelect from './components/assets/ThemeSelect.vue'
import router from './router/index.js'
import store from './store/index.js'

/* Adds a module to the store which is reactive to route parameter changes.
 * This allows other modules to work reactively with route changes */
sync(store, router)

Vue.config.productionTip = false
Vue.use(Toasted, {
    position: 'top-center',
    duration: 4000,
})
Vue.use(flatPickr)
Vue.use(VueIntro)

Vue.component('icon', Icon)
Vue.component('theme-select', ThemeSelect)
Vue.component('reset-wrapper', ResetWrapper)

initSentry(Vue)
initBootstrap(Vue)
initGlobalHelpers(Vue)

/* Checks the store for for permissions according to the current route cID or aID. */
Vue.prototype.$hasPermission = store.getters['permissions/hasPermission']

/* Checks for object equality, where comparison of values null and '' yields true */
Vue.prototype.$_isEqual = (obj1, obj2) => isEqualWith(obj1, obj2, (a, b) => {
    if ((a === null || a === '') && (b === null || b === '')) {
        return true
    }
    return undefined // default comparison should take place
})

const toApi = new RegExp(`^${CustomEnv.API_URL}`)

/* eslint-disable */
Vue.config.productionTip = false;

(function (open, send) {
    let xhrOpenRequestUrl;

    XMLHttpRequest.prototype.open = function (_, url) {
        xhrOpenRequestUrl = url
        open.apply(this, arguments)
    }

    XMLHttpRequest.prototype.send = function () {
        if (store.getters['user/jwtAccess'] && toApi.test(xhrOpenRequestUrl)) {
            this.setRequestHeader('Authorization', `Bearer ${store.getters['user/jwtAccess']}`)
        }
        send.apply(this, arguments)
    }
})(XMLHttpRequest.prototype.open, XMLHttpRequest.prototype.send)
/* eslint-enable */

/* eslint-disable no-new */
new Vue({
    el: '#app',
    router,
    store,
    components: { App },
    data: {
        borderColors: ['border-pink', 'border-purple', 'border-yellow', 'border-blue'],
        previousPage: null,
        windowWidth: 0,
        maxFileSizeBytes: 10485760,
        maxEmailFileSizeBytes: 10485760,
        flatPickrTimeConfig: {
            enableTime: true,
            time_24hr: true,
            defaultHour: 23,
            defaultMinute: 59,
            altInput: true,
            altFormat: 'D d M Y H:i',
            dateFormat: 'Y-m-dTH:i:S',
            disableMobile: true,
        },
        flatPickrConfig: {
            enableTime: false,
            altInput: true,
            altFormat: 'D d M Y',
            dateFormat: 'Y-m-d',
            disableMobile: true,
        },
        fileTypes: {
            // https://developer.mozilla.org/en-US/docs/Web/HTML/Element/Img
            // Only used extensions that are supported by all named browsers
            // No: apng (IE), webp (IE, Safari), tiff (all)
            img: 'bmp, gif, ico, cur, jpg, jpeg, jfif, pjpeg, pjp, png, svg',
            pdf: 'pdf',
        },
    },
    computed: {
        /* Bootstrap breakpoints for custom events. */
        // TODO Figure out how to get these from the dedicated sass file (more webpack fun)
        sm () { return this.windowWidth > 575 },
        md () { return this.windowWidth > 767 },
        lg () { return this.windowWidth > 991 },
        xl () { return this.windowWidth > 1199 },
        xsMax () { return this.windowWidth < 576 },
        smMax () { return this.windowWidth < 769 },
        mdMax () { return this.windowWidth < 992 },
        lgMax () { return this.windowWidth < 1200 },
    },
    created () {
        store.dispatch('connection/setupConnectionInterceptors', { connection: connection.conn })
        store.dispatch('connection/setupConnectionInterceptors',
            { connection: connection.connRefresh, isRefresh: true })
        store.dispatch('connection/setupConnectionInterceptors', { connection: connection.connUpFile })
        store.dispatch('connection/setupConnectionInterceptors', { connection: connection.connDownFile })

        window.addEventListener('resize', () => {
            this.windowWidth = window.innerWidth
        })
        this.windowWidth = window.innerWidth
    },
    methods: {
        getBorderClass (id) {
            return this.borderColors[id % this.borderColors.length]
        },
        beautifyDate (date, displayDate = true, displayTime = true) {
            if (!date) {
                return ''
            }
            const year = date.substring(0, 4)
            const month = date.substring(5, 7)
            const day = date.substring(8, 10)
            const time = date.substring(11, 16)
            let s = ''
            if (displayDate) {
                s += `${day}-${month}-${year}`
            }
            if (displayDate && displayTime) {
                s += ' at '
            }
            if (displayTime) {
                s += time
            }
            return s
        },
        assignmentRoute (assignment, course = null) {
            const route = {
                params: {
                    cID: course === null ? assignment.course.id : course.id,
                    aID: assignment.id,
                },
            }

            if (this.$hasPermission('can_view_all_journals', 'assignment', assignment.id)) {
                if (!assignment.is_published && !assignment.is_group_assignment) { // Teacher not published route
                    route.name = 'AssignmentEditor'
                } else { // Teacher published route
                    route.name = 'Assignment'
                }
            } else if (assignment.is_group_assignment && assignment.journal === null) {
                // Student new group assignment route
                route.name = 'JoinJournal'
            } else if (assignment.journal) { // Student with journal route
                route.name = 'Journal'
                route.params.jID = assignment.journal
            } else {
                route.name = 'Home'
                this.$store.commit('sentry/CAPTURE_SCOPED_MESSAGE', {
                    msg: 'Assignment route not found, redirected to homepage',
                    extra: {
                        routeQuery: this.$route.query,
                        routeParams: this.$route.params,
                        assignment,
                    },
                })
            }

            return route
        },
        canGradeForSomeCourse () {
            return Object.entries(this.$store.getters['user/permissions']).some(
                ([key, value]) => ((key.indexOf('assignment') >= 0) && value.can_grade))
        },
    },
    render: (h) => h(App),
    template: '<App/>',
}).$mount('#app')
