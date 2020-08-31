<template>
    <content-single-column>
        <div v-if="handleUserIntegration">
            <h1 class="theme-h1 mb-2">
                <span>Welcome to eJournal!</span>
            </h1>
            <b-card class="no-hover">
                <h2 class="theme-h2 multi-form">
                    Hi {{ lti.fullName ? lti.fullName : lti.username }}
                </h2>
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
                        :lti="lti"
                        class="mt-2"
                        @handleAction="userIntegrated"
                    />
                </template>
            </b-card>

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
import loadSpinner from '@/components/loading/LoadSpinner.vue'
import registerUser from '@/components/account/RegisterUser.vue'
import loginForm from '@/components/account/LoginForm.vue'

import userAPI from '@/api/user.js'

export default {
    name: 'LtiLogin',
    components: {
        contentSingleColumn,
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
                state: '',
                key_error: '-2',
                bad_auth: '-1',
                no_user: '0',
                logged_in: '1',
            },

            lti: {
                ltiJWT: '',
                fullName: '',
                username: '',
                email: '',
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
        if (this.$route.query.state === this.states.bad_auth) {
            this.$router.push({
                name: 'ErrorPage',
                params: {
                    code: '511',
                    reasonPhrase: 'Network authorization required',
                    description: `Invalid credentials from the LTI environment.
                                  Please contact the system administrator.`,
                },
            })
        } else if (this.$route.query.state === this.states.key_error) {
            this.$router.push({
                name: 'ErrorPage',
                params: {
                    code: '400',
                    reasonPhrase: 'Missing parameter in LTI request',
                    description: `${this.$route.query.description}
                    Please contact the system administrator.`,
                },
            })
        } else {
            this.lti.ltiJWT = this.$route.query.lti_params

            /* The LTI parameters are verified in our backend, and the corresponding user is logged in. */
            if (this.$route.query.state === this.states.logged_in) {
                this.$store.commit(
                    'user/SET_JWT',
                    { access: this.$route.query.jwt_access, refresh: this.$route.query.jwt_refresh },
                )
                this.$store.dispatch('user/populateStore').then(() => {
                    this.userIntegrated()
                }, (error) => {
                    this.$router.push({
                        name: 'ErrorPage',
                        params: {
                            code: error.response.status,
                            reasonPhrase: error.response.statusText,
                            description: 'Could not fetch all user data, please try again.',
                        },
                    })
                })

            /* The LTI parameters are verified in our backend, however there is no corresponding user yet.
               We must create/connect one. */
            } else if (this.$route.query.state === this.states.no_user) {
                this.$store.commit('user/LOGOUT') // Ensures no old user is loaded from local storage.
                if (this.$route.query.full_name !== undefined) {
                    this.lti.fullName = this.$route.query.full_name
                }
                if (this.$route.query.username !== undefined) {
                    this.lti.username = this.$route.query.username
                }
                if (this.$route.query.email !== undefined) {
                    this.lti.email = this.$route.query.email
                }
                if (this.$route.query.username_already_exists === 'True') {
                    this.usernameAlreadyExists = true
                }

                this.handleUserIntegration = true
            } else {
                this.$router.push({
                    name: 'ErrorPage',
                    params: {
                        code: '500',
                        reasonPhrase: 'Internal Server Error',
                        description: `Received invalid state from the server
                                      when trying to integrate the new user.
                                      Please contact the system administrator
                                      for more information. Further integration
                                      is not possible.`,
                    },
                })
            }
        }
    },
    methods: {
        userIntegrated () {
            this.$router.push({
                name: 'LtiLaunch',
                query: {
                    ltiJWT: this.lti.ltiJWT,
                },
            })
        },
        showModal (ref) {
            this.$refs[ref].show()
        },
        hideModal (ref) {
            this.$refs[ref].hide()
        },
        handleLinked () {
            userAPI.update(0, { jwt_params: this.lti.ltiJWT })
                .then(() => {
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
