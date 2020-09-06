<template>
    <!-- eslint-disable vue/attribute-hyphenation -->
    <div>
        Our team has been notified. If you'd like to help, tell us what happened below.
        <b-form
            class="mt-2"
            @submit.prevent="sendSentryFeedback()"
        >
            <b-form-group
                v-if="!userLoggedIn"
                label="Name"
                label-for="form-sentry-feedback-name"
            >
                <b-form-input
                    id="form-sentry-feedback-name"
                    v-model="name"
                    class="theme-input multi-form"
                    required
                    placeholder="Jane Doe"
                />
            </b-form-group>

            <b-form-group
                v-if="!userLoggedIn"
                label="Email"
                label-for="form-sentry-feedback-email"
            >
                <b-form-input
                    id="form-sentry-feedback-email"
                    v-model="email"
                    class="theme-input multi-form"
                    type="email"
                    required
                    placeholder="jane@example.com"
                />
            </b-form-group>

            <b-form-group
                :label="userLoggedIn ? null : 'What happenend?'"
                label-for="form-sentry-feedback-description"
            >
                <b-form-textarea
                    id="form-sentry-feedback-description"
                    v-model="description"
                    class="theme-input"
                    required
                    placeholder="I clicked on 'X' and then hit 'Confirm'"
                />
            </b-form-group>

            <b-button :to="{name: 'Home'}">
                <icon name="home"/>
                Home
            </b-button>

            <b-button
                class="float-right"
                type="submit"
            >
                <icon name="paper-plane"/>
                Submit
            </b-button>
        </b-form>
    </div>
</template>

<script>
import connection from '@/api/connection.js'
import { mapGetters } from 'vuex'

export default {
    name: 'SentryFeedbackForm',
    data () {
        return {
            name: null,
            email: null,
            description: null,
        }
    },
    computed: {
        ...mapGetters({
            userLoggedIn: 'user/loggedIn',
            userFullName: 'user/fullName',
            userEmail: 'user/email',
            sentryLastEventID: 'sentry/lastEvenID',
        }),
    },
    created () {
        if (this.userLoggedIn) {
            this.name = this.userFullName
            this.email = this.userEmail
        }
    },
    methods: {
        sendSentryFeedback () {
            connection.connSentry.post('user-feedback/', {
                comments: this.description,
                email: this.email,
                event_id: this.sentryLastEventID,
                name: this.name,
            })
            this.$toasted.success('Thank you for your report!')
            this.$router.push({ name: 'Home' })
        },
    },
}
</script>
