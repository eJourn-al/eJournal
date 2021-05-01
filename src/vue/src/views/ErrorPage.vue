<template>
    <content-single-column>
        <h1 class="theme-h1 mb-2">
            <icon
                name="exclamation-circle"
                scale="1.75"
                class="fill-red mr-1 shift-up-5"
            />
            Error {{ code }}: {{ reasonPhrase }}
        </h1>
        <b-card class=" max-width-600">
            <span
                class="d-block"
            >
                <template v-if="description !== null">
                    {{ description }}
                </template>
                <template v-else>
                    We are sorry, but an unknown error has brought you here.
                </template>
            </span>
            <sentry-feedback-form
                v-if="sentryLastEventID !== null"
                class="sentry-feedback-form"
            />
            <b-button
                v-else
                slot="footer"
                class="blue-filled-button"
                :to="{name: 'Home'}"
            >
                <icon name="home"/>
                Home
            </b-button>
        </b-card>
    </content-single-column>
</template>

<script>
import { mapGetters } from 'vuex'
import contentSingleColumn from '@/components/columns/ContentSingleColumn.vue'
import sentryFeedbackForm from '@/components/sentry/SentryFeedbackForm.vue'

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
