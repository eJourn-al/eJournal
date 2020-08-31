<template>
    <content-single-column>
        <h1 class="theme-h1 mb-2">
            <span>
                Error {{ code }}: {{ reasonPhrase }}
            </span>
        </h1>
        <b-card
            class="no-hover border-dark-grey max-width-600"
        >
            <h2
                v-if="description !== null"
                class="theme-h2 mb-2"
            >
                {{ description }}
            </h2>
            <span
                v-else
                class="d-block multi-form"
            >
                We are sorry, but an unknown error has brought you here.
            </span>
            <!-- TODO: Enable once feedbacklink is fixed -->
            <sentry-feedback-form
                v-if="sentryLastEventID !== null && false"
                class="sentry-feedback-form"
            />
            <b-button
                v-else
                :to="{name: 'Home'}"
            >
                <icon name="home"/>
                Home
            </b-button>
        </b-card>
    </content-single-column>
</template>

<script>
import contentSingleColumn from '@/components/columns/ContentSingleColumn.vue'
import sentryFeedbackForm from '@/components/sentry/SentryFeedbackForm.vue'
import { mapGetters } from 'vuex'

export default {
    name: 'ErrorPage',
    components: {
        sentryFeedbackForm,
        contentSingleColumn,
    },
    props: {
        code: {
            default: '520',
        },
        reasonPhrase: {
            default: 'Unknown Error',
        },
        description: {
            default: null,
        },
    },
    computed: {
        ...mapGetters({
            sentryLastEventID: 'sentry/lastEvenID',
        }),
    },
}
</script>

<style lang="sass">
.max-width-600
    max-width: 600px
</style>
