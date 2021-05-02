<template>
    <div
        v-if="userLoggedIn"
        class="feedback-wrapper"
    >
        <div
            class="feedback-button"
            @click="showModal('feedbackModal')"
        >
            <icon
                name="life-ring"
                scale="1"
                class="shift-up-2"
            />
            Support
        </div>

        <b-modal
            ref="feedbackModal"
            size="lg"
            noEnforceFocus
        >
            <template #modal-title>
                Support
                <div
                    v-b-tooltip.hover
                    title="Support available in English and Dutch"
                    class="d-inline ml-2"
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
            </template>
            Hi {{ userFullName }}, thanks for reaching out to eJournal support.
            Please select the support category that best fits your situation:
            <div
                :class="{ 'input-disabled': !$store.getters['user/verifiedEmail'] }"
                class="full-width d-flex justify-content-center mt-2"
            >
                <b-button
                    class="red-button mr-2 flex-grow-1"
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
                        contentPlaceholder = 'It would be nice if I could do \'X\' instead of having to do \'Y\''
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
                    class="mb-2"
                    type="text"
                    required
                />

                <b-form-textarea
                    v-model="feedback"
                    :rows="4"
                    :placeholder="contentPlaceholder"
                    class="mb-2"
                    required
                />
                <b-form-file
                    ref="fileinput"
                    v-model="files"
                    class="fileinput mb-2"
                    multiple
                    placeholder="Add an attachment (optional)"
                    @change="filesHandler"
                />
            </div>
            <template #modal-footer>
                <b-button
                    :class="{'input-disabled': !type }"
                    @click="sendFeedback()"
                >
                    <icon name="paper-plane"/>
                    Send
                </b-button>
            </template>
        </b-modal>
    </div>
</template>

<script>
import { mapGetters } from 'vuex'
import connection from '@/api/connection.js'
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

                feedbackAPI.sendFeedback(data, {}, { responseSuccessToast: true })
                if (this.type === 'bug' && this.sentryLastEventID) {
                    connection.connSentry.post('/user-feedback/', {
                        comments: `Topic: ${this.topic}\n\nFeedback: ${this.feedback}`,
                        email: this.userEmail,
                        event_id: this.sentryLastEventID,
                        name: this.userFullName,
                    })
                }

                this.resetFeedback()
                this.hideModal('feedbackModal')
            }
        },
        resetFeedback () {
            this.topic = ''
            this.type = null
            this.feedback = ''
            this.files = null
            this.$refs.fileinput.reset()
        },
        showModal (ref) {
            this.$refs[ref].show()
        },
        hideModal (ref) {
            this.$refs[ref].hide()
        },
    },
}
</script>

<style lang="sass">
.feedback-wrapper
    position: fixed
    bottom: 0px
    z-index: 1200
    .feedback-button
        cursor: pointer
        padding: 2px 10px 2px 10px
        position: fixed
        bottom: 0px
        right: 150px
        background-color: white
        border: 1px solid $border-color
        border-bottom-width: 0px
        border-radius: 10px 10px 0px 0px !important
        &, svg
            color: $theme-dark-blue
            transition: all 0.3s cubic-bezier(.25,.8,.25,1) !important
        &:hover
            background-color: $theme-blue
            border-color: $theme-blue
            &, svg
                color: white

.support-lang-flag
    height: 0.7em
    margin-top: -4px
    border-radius: 4px !important
</style>
