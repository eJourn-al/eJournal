<template>
    <content-single-column>
        <h1 class="theme-h1">
            <span>
                You're early!
            </span>
        </h1>
        <b-card
            class="no-hove max-width-600"
        >
            <h2 class="theme-h2 mb-2">
                This assignment is not ready yet
            </h2>
            <p class="multi-form">
                The assignment you are looking for is not yet configured by your instructor.
                Please ask them to visit the assignment through Canvas first, or come back at a later time
                once your instructor has completed configuration.
            </p>
            <b-button
                v-if="knownAssignment"
                :to="{name: 'Home'}"
            >
                <icon name="home"/>
                Home
            </b-button>
        </b-card>
    </content-single-column>
</template>

<script>
import * as Sentry from '@sentry/browser'
import contentSingleColumn from '@/components/columns/ContentSingleColumn.vue'

export default {
    name: 'NotSetup',
    components: {
        contentSingleColumn,
    },
    props: {
        courseName: {
            default: null,
        },
        assignmentName: {
            default: null,
        },
        ltiState: {
            default: null,
        },
    },
    computed: {
        knownAssignment () {
            if (!this.$store.getters['user/loggedIn']) { return false }
            return Object.keys(this.$store.getters['user/permissions']).some(key => key.indexOf('assignment') > -1)
        },
    },
    mounted () {
        Sentry.withScope((scope) => {
            scope.setLevel('warning')
            scope.setTag('not_setup', this.ltiState)
            scope.setExtra('launch_id', this.$route.query.launch_id)
            Sentry.captureMessage('User requested access to content which was not yet setup.')
        })
    },
}
</script>

<style lang="sass">
.max-width-600
    max-width: 600px
</style>
