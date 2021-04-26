import { detect as detectBrowser } from 'detect-browser'
import AdminPanel from '@/views/AdminPanel.vue'
import Assignment from '@/views/Assignment.vue'
import Course from '@/views/Course.vue'
import Home from '@/views/Home.vue'
import Journal from '@/views/Journal.vue'
import Login from '@/views/Login.vue'
import Logout from '@/views/Logout.vue'
import LtiLaunch from '@/views/LtiLaunch.vue'
import LtiLogin from '@/views/LtiLogin.vue'
import Router from 'vue-router'
import Vue from 'vue'
import routerConstraints from '@/utils/constants/router_constraints.js'
import store from '@/store/index.js'

Vue.use(Router)

const router = new Router({
    mode: 'history',
    routes: [{
        path: '/',
        name: 'Guest',
        component: () => import(/* webpackChunkName: 'guest' */ '@/views/Guest.vue'),
    }, {
        path: '/Home',
        name: 'Home',
        component: Home,
    }, {
        path: '/AdminPanel',
        name: 'AdminPanel',
        component: AdminPanel,
    }, {
        path: '/Login',
        name: 'Login',
        component: Login,
    }, {
        path: '/SetPassword/:username/:token',
        name: 'SetPassword',
        component: () => import(/* webpackChunkName: 'password-recovery' */ '@/views/SetPassword.vue'),
        props: true,
    }, {
        path: '/EmailVerification/:username/:token',
        name: 'EmailVerification',
        component: () => import(/* webpackChunkName: 'email-verification' */ '@/views/EmailVerification.vue'),
        props: true,
    }, {
        path: '/Register',
        name: 'Register',
        component: () => import(/* webpackChunkName: 'register' */ '@/views/Register.vue'),
    }, {
        path: '/Profile',
        name: 'Profile',
        component: () => import(/* webpackChunkName: 'profile' */ '@/views/Profile.vue'),
    }, {
        path: '/LtiLaunch',
        name: 'LtiLaunch',
        component: LtiLaunch,
    }, {
        path: '/LtiLogin',
        name: 'LtiLogin',
        component: LtiLogin,
    }, {
        path: '/AssignmentsOverview',
        name: 'AssignmentsOverview',
        component: () => import(/* webpackChunkName: 'assignments-overview' */ '@/views/AssignmentsOverview.vue'),
    }, {
        path: '/Error',
        name: 'ErrorPage',
        component: () => import(/* webpackChunkName: 'error-page' */ '@/views/ErrorPage.vue'),
        props: true,
    }, {
        path: '/NotSetup',
        name: 'NotSetup',
        component: () => import(/* webpackChunkName: 'not-setup' */ '@/views/NotSetup.vue'),
        props: true,
    }, {
        path: '/Logout',
        name: 'Logout',
        component: Logout,
    }, {
        path: '/Home/Course/:cID',
        name: 'Course',
        component: Course,
        props: (route) => ({
            cID: Number.parseInt(route.params.cID, 10),
        }),
    }, {
        path: '/Home/Course/:cID/CourseEdit',
        name: 'CourseEdit',
        component: () => import(/* webpackChunkName: 'course-edit' */ '@/views/CourseEdit.vue'),
        props: (route) => ({
            cID: Number.parseInt(route.params.cID, 10),
        }),
    }, {
        path: '/Home/Course/:cID/CourseEdit/UserRoleConfiguration',
        name: 'UserRoleConfiguration',
        component: () => import(/* webpackChunkName: 'role-config' */ '@/views/UserRoleConfiguration.vue'),
        props: (route) => ({
            cID: Number.parseInt(route.params.cID, 10),
        }),
    }, {
        path: '/Home/Course/:cID/Assignment/:aID',
        name: 'Assignment',
        component: Assignment,
        props: (route) => ({
            cID: Number.parseInt(route.params.cID, 10),
            aID: Number.parseInt(route.params.aID, 10),
        }),
    }, {
        path: '/Home/Course/:cID/Assignment/:aID/AssignmentEditor',
        name: 'AssignmentEditor',
        component: () => import(/* webpackChunkName: 'format-edit' */ '@/views/AssignmentEditor.vue'),
        props: (route) => ({
            cID: Number.parseInt(route.params.cID, 10),
            aID: Number.parseInt(route.params.aID, 10),
        }),
    }, {
        path: '/Home/Course/:cID/Assignment/:aID/Journal/New',
        name: 'JoinJournal',
        component: () => import(/* webpackChunkName: 'join-journal' */ '@/views/JoinJournal.vue'),
        props: (route) => ({
            cID: Number.parseInt(route.params.cID, 10),
            aID: Number.parseInt(route.params.aID, 10),
        }),
    }, {
        path: '/Home/Course/:cID/Assignment/:aID/Journal/:jID',
        name: 'Journal',
        component: Journal,
        props: (route) => ({
            cID: Number.parseInt(route.params.cID, 10),
            aID: Number.parseInt(route.params.aID, 10),
            jID: Number.parseInt(route.params.jID, 10),
        }),
    }, {
        path: '*',
        name: 'NotFound',
        component: () => import(/* webpackChunkName: 'error-page' */ '@/views/ErrorPage.vue'),
        props: {
            code: '404',
            reasonPhrase: 'Not Found',
            description: 'We\'re sorry but we can\'t find the page you tried to access.',
        },
    }],
})

// Minimal supported browser versions
const SUPPORTED_BROWSERS = {
    chrome: 78,
    safari: 11,
    firefox: 68,
    'edge-chromium': 79,
    edge: 79,
    ie: 12,
}

/* Obtain browser user agent data. */
const browser = detectBrowser()
let browserUpdateNeeded = (browser && browser.name && browser.version && SUPPORTED_BROWSERS[browser.name]
    && parseInt(browser.version.split('.')[0], 10) < SUPPORTED_BROWSERS[browser.name])

router.beforeEach((to, from, next) => {
    const loggedIn = store.getters['user/loggedIn']

    if (from.name) {
        router.app.previousPage = from
    }

    /* Show warning when user visits the website with an outdated browser (to ensure correct functionality).
     * In case the browser is not in our whitelist, no message will be shown. */
    if (browserUpdateNeeded && !(to.name === 'Logout' || from.name === 'Guest' || from.name === 'Login')) {
        router.app.$toasted.clear() // Clear existing toasts.
        setTimeout(() => { // Allow a cooldown for smoother transitions.
            router.app.$toasted.clear() // Clear existing toasts.
            router.app.$toasted.error('Your current browser version is not up to date. For an optimal experience, '
                + 'please update your browser before using eJournal.', {
                action: [
                    {
                        text: 'Info',
                        onClick: (e, toastObject) => {
                            window.open('https://browsehappy.com', '_blank')
                            toastObject.goAway(0)
                        },
                    },
                    {
                        text: 'Dismiss',
                        onClick: (e, toastObject) => {
                            browserUpdateNeeded = false
                            toastObject.goAway(0)
                        },
                    },
                ],
                duration: null,
            })
        }, 1000)
    }

    if (loggedIn && routerConstraints.UNAVAILABLE_WHEN_LOGGED_IN.has(to.name)) {
        next({ name: 'Home' })
    } else if (loggedIn && to.name === 'AdminPanel' && !store.getters['user/isSuperuser']) {
        router.app.$toasted.error('You are not allowed to access that page.')
        next({ name: 'Home' })
    } else if (!loggedIn && !routerConstraints.PERMISSIONLESS_CONTENT.has(to.name)) {
        store.dispatch('user/validateToken')
            .then(() => { next() })
            .catch(() => {
                router.app.previousPage = to
                next({ name: 'Login' })
            })
    } else { next() }
})

router.afterEach((to, from) => {
    store.dispatch('instance/retrieve', {})

    if ('aID' in to.params) {
        store.dispatch('assignment/retrieve', { id: to.params.aID })
        store.dispatch('presetNode/list', { aID: to.params.aID })
        store.dispatch('category/list', { aID: to.params.aID })
        store.dispatch('template/list', { aID: to.params.aID })

        if ('aID' in from.params && parseInt(to.params.aID, 10) !== parseInt(from.params.aID, 10)) {
            store.commit('category/CLEAR_FILTERED_CATEGORIES')
        }
    }
})

export default router
