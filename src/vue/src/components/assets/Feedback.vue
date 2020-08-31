<template>
    <b-card class="no-hover">
        <h2 class="theme-h2 multi-form">
            How can we help you?
            <div
                v-b-tooltip.hover
                title="Support available in English and Dutch"
                class="d-inline"
            >
                <img
                    src="/gb-flag.svg"
                    class="theme-img support-lang-flag mr-1"
                />
                <img
                    src="/nl-flag.svg"
                    class="theme-img support-lang-flag"
                />
            </div>
        </h2>
        Hi {{ $store.getters['user/fullName'] }}, thanks for reaching out to eJournal support.
        Please select the support category that best fits your situation:
        <div
            :class="{ 'input-disabled': !$store.getters['user/verifiedEmail'] }"
            class="full-width d-flex justify-content-center mt-2"
        >
            <b-button
                class="delete-button mr-2 flex-grow-1"
                :class="{'active': type === 'bug'}"
                @click="() => {
                    type = 'bug'
                    topicPlaceholder = 'Something went wrong while using eJournal'
                    contentPlaceholder = 'I clicked on \'X\' and then an error appeared...'
                }"
            >
                <icon name="bug"/>
                Bug
            </b-button>
            <b-button
                class="mr-2 flex-grow-1"
                :class="{'active': type === 'help'}"
                @click="() => {
                    type = 'help'
                    topicPlaceholder = 'I could use some help while using eJournal'
                    contentPlaceholder = 'How does feature \'X\' work? Help is much appreciated!'
                }"
            >
                <icon name="info-circle"/>
                Help
            </b-button>
            <b-button
                class="flex-grow-1"
                :class="{'active': type === 'feedback'}"
                @click="() => {
                    type = 'feedback'
                    topicPlaceholder = 'I have a suggestion for a new feature, or...'
                    contentPlaceholder = 'It would be nice if I would be able to do \'X\' instead of having to do \'Y\''
                }"
            >
                <icon name="envelope"/>
                Feedback
            </b-button>
        </div>
        <b-alert
            v-if="!$store.getters['user/verifiedEmail']"
            show
            class="mt-3 mb-0"
        >
            Support is only available for users with a verified email address.
            Please verify your email address on your
            <a
                href="/Profile"
            >
                <b>profile</b>
            </a>.
        </b-alert>
        <div v-if="type">
            <hr/>
            <b-input
                v-model="topic"
                :placeholder="topicPlaceholder"
                class="theme-input multi-form"
                type="text"
                required
            />

            <b-form-textarea
                v-model="feedback"
                :rows="4"
                :placeholder="contentPlaceholder"
                class="theme-input multi-form"
                required
            />
            <b-form-file
                ref="fileinput"
                v-model="files"
                class="fileinput multi-form"
                multiple
                placeholder="Add an attachment (optional)"
                @change="filesHandler"
            />
            <b-button
                class="float-right"
                @click="$emit(sendFeedback())"
            >
                <icon name="paper-plane"/>
                Send
            </b-button>
        </div>
    </b-card>
</template>

<script>
import connection from '@/api/connection.js'
import { mapGetters } from 'vuex'
import feedbackAPI from '@/api/feedback.js'

export default {
    data () {
        return {
            topic: '',
            feedback: '',
            type: null,
            topicPlaceholder: null,
            contentPlaceholder: null,
            types: [
                'bug', 'help', 'feedback',
            ],
            files: null,
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
    methods: {
        filesHandler (e) {
            const files = e.target.files
            if (files.length < 1) { return }

            let uploadSize = 0
            for (let i = 0; i < files.length; i++) {
                uploadSize += files[i].size
                if (uploadSize > this.$root.maxEmailFileSizeBytes) {
                    this.$toasted.error('The selected files exceed the total maximum file size of: 10 mb.')
                    this.$refs.fileinput.reset()
                    this.files = null
                    return
                }
            }

            this.files = files
        },
        sendFeedback () {
            if (this.topic === '') {
                this.$toasted.error('Please fill in a topic')
            } else if (this.type == null) {
                this.$toasted.error('Please choose a support category')
            } else if (this.feedback === '') {
                this.$toasted.error('Please enter your message')
            } else {
                const data = new FormData()
                data.append('topic', this.topic)
                data.append('ftype', this.type)
                data.append('feedback', this.feedback)
                data.append('user_agent', navigator.userAgent)
                data.append('url', window.location.href)
                if (this.files != null) {
                    for (let i = 0; i < this.files.length; i++) {
                        data.append('files', this.files[i])
                    }
                }

                feedbackAPI.sendFeedback(data, { responseSuccessToast: true })
                if (this.type === 'bug' && this.sentryLastEventID) {
                    connection.connSentry.post('/user-feedback/', {
                        comments: `Topic: ${this.topic}\n\nFeedback: ${this.feedback}`,
                        email: this.userEmail,
                        event_id: this.sentryLastEventID,
                        name: this.userFullName,
                    })
                }

                this.resetFeedback()
                return 'feedbackSent'
            }

            return 'feedbackNotSent'
        },
        resetFeedback () {
            this.topic = ''
            this.type = null
            this.feedback = ''
            this.files = null
            this.$refs.fileinput.reset()
        },
    },
}
</script>

<style lang="sass">
.support-lang-flag
    height: 0.8em
    margin-top: -5px
    border-radius: 2px !important
</style>
