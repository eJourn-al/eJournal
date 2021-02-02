import * as Sentry from '@sentry/browser'
import { Vue as SentryVueIntegration } from '@sentry/integrations'
import store from '@/store/index.js'


function beforeSend (event, hint) { // eslint-disable-line no-unused-vars
    // Filtering can be done here https://docs.sentry.io/error-reporting/configuration/filtering/?platform=browser
    if (event.exception) {
        store.commit('sentry/SET_LAST_EVENT_ID', { eventID: event.event_id })
    }

    /* Set user context if missing, e.g. after store hydration.
     * NOTE: Directly setting user context after store hydration is not possible as Sentry is then not fully
     * initialized. */
    if (!('user' in event) && store.getters['user/storePopulated']) {
        /* Set user context for future sentry events. */
        store.commit('sentry/SET_SENTRY_USER_SCOPE', store.getters['user/storePopulated'])
        /* Set user context for the already generated event. */
        event.user = store.getters['user/relevantUserSentryState']
    }

    if (hint && hint.originalException) {
        const originalException = hint.originalException

        if (event.extra === undefined) { event.extra = {} }
        if (originalException.config) { event.extra.config = originalException.config }
        if (originalException.request) { event.extra.request = originalException.request }
        if (originalException.response) { event.extra.response = originalException.response }
    }

    return event
}

export default function initSentry (Vue) {
    /* NOTE: Release key is configured by the SentryWebpackPlugin */
    Sentry.init({
        dsn: CustomEnv.SENTRY_DSN,
        /* LogErrors: still call Vue's original logError function as well. */
        integrations: [new SentryVueIntegration({ Vue, attachProps: true, logErrors: true })],
        beforeSend,
    })
}
