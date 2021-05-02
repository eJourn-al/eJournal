<template>
    <content-single-column class="not-logged-in-page">
        <img
            class="not-logged-in-page-logo"
            src="ejournal-logo.svg"
        />
        <div v-if="handleUserIntegration">
            <b-card>
                <h2
                    slot="header"
                    class="theme-h2"
                >
                    Welcome to eJournal
                </h2>
                Hi {{ lti.fullName ? lti.fullName : lti.username }},
                <template v-if="usernameAlreadyExists">
                    <p>
                        It looks like you already have an account on eJournal. Please verify this by logging in below.
                        If this is not the case, reach out to us at
                        <a
                            href="mailto:support@eJournal.app"
                            target="_blank"
                            class="text-blue"
                        >
                            support@eJournal.app
                        </a>.
                    </p>
                    <login-form @handleAction="handleLinked"/>
                </template>
                <template v-else>
                    <p>
                        You are ready to start using eJournal as soon as you configure a password below.
                        This allows you to access eJournal directly at
                        <a
                            :href="domainUrl"
                            target="_blank"
                        >
                            {{ domain }}
                        </a>, as well as via Canvas like you did just now.
                    </p>
                    <p>
                        Do you already have an existing eJournal account?
                        <a
                            href=""
                            class="text-blue"
                            @click.prevent.stop="showModal('linkUserModal')"
                        >
                            <u>Click here</u>
                        </a> to link it instead.
                    </p>
                    <register-user
                        :launchId="this.$route.query.launch_id"
                        class="mt-2"
                        @handleAction="userIntegrated"
                    />
                </template>
            </b-card>
            <custom-footer/>

            <b-modal
                ref="linkUserModal"
                title="Link to existing eJournal account"
                size="lg"
                hideFooter
                noEnforceFocus
            >
                <login-form @handleAction="handleLinked"/>
            </b-modal>
        </div>
        <load-spinner
            v-else
            class="mt-5"
        />
    </content-single-column>
</template>

<script>
import contentSingleColumn from '@/components/columns/ContentSingleColumn.vue'
import customFooter from '@/components/assets/Footer.vue'
import loadSpinner from '@/components/loading/LoadSpinner.vue'
import loginForm from '@/components/account/LoginForm.vue'
import registerUser from '@/components/account/RegisterUser.vue'

import userAPI from '@/api/user.js'

export default {
    name: 'LtiLogin',
    components: {
        contentSingleColumn,
        customFooter,
        loadSpinner,
        registerUser,
        loginForm,
    },
    data () {
        return {
            /* Variables for loading the right component. */
            handleUserIntegration: false,

            /* Possible states for the control flow */
            states: {
                noUser: '0',
            },

            usernameAlreadyExists: false,
        }
    },
    computed: {
        domain () {
            return window.location.host
        },
        domainUrl () {
            return window.location.origin
        },
    },
    mounted () {
        if (this.$route.query.launch_state === this.states.noUser) {
            /* The LTI parameters are verified in our backend, however there is no corresponding user yet.
            We must create/connect one. */
            this.$store.commit('user/LOGOUT') // Ensures no old user is loaded from local storage.
            if (this.$route.query.username_already_exists === 'True') {
                this.usernameAlreadyExists = true
            }

            this.handleUserIntegration = true
        } else {
            /* The LTI parameters are verified in our backend, and the corresponding user is logged in. */
            this.$store.commit(
                'user/SET_JWT',
                { access: this.$route.query.jwt_access, refresh: this.$route.query.jwt_refresh },
            )
            this.$store.dispatch('user/populateStore').then(this.userIntegrated)
        }
    },
    methods: {
        showModal (ref) {
            this.$refs[ref].show()
        },
        hideModal (ref) {
            this.$refs[ref].hide()
        },
        userIntegrated () {
            this.$router.push({
                name: 'LtiLaunch',
                query: this.$route.query,
            })
        },
        handleLinked () {
            userAPI.update(0, { launch_id: this.$route.query.launch_id })
                .then((user) => {
                    this.$route.query.launch_state = user.launch_state
                    /* This is required because between the login and the connect of lti user to our user
                      data can change. */
                    this.$store.dispatch('user/populateStore').then(() => {
                        this.hideModal('linkUserModal')
                        this.userIntegrated()
                    })
                })
        },
    },
}
</script>
