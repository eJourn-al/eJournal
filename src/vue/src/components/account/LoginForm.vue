<template>
    <div>
        <b-card class="no-hover card-last-elem-button">
            <b-form @submit.prevent="handleLogin()">
                <h2 class="theme-h2 field-heading">
                    Username
                </h2>
                <b-input
                    v-model="username"
                    class="multi-form theme-input"
                    autofocus
                    required
                    placeholder="Username"
                    autocomplete="username"
                />
                <h2 class="theme-h2 field-heading">
                    Password
                </h2>
                <b-input
                    v-model="password"
                    class="multi-form theme-input"
                    type="password"
                    required
                    placeholder="Password"
                    autocomplete="current-password"
                />
                <b-button
                    class="float-right multi-form"
                    type="submit"
                >
                    <icon name="sign-in-alt"/>
                    Log in
                </b-button>
                <b-button
                    v-b-modal.forgotPasswordModal
                    class="multi-form orange-button mr-2"
                >
                    <icon name="question"/>
                    Forgot password
                </b-button>
                <b-button
                    v-if="allowRegistration"
                    :to="{ name: 'Register' }"
                    class="multi-form"
                >
                    <icon name="user-plus"/>
                    Register
                </b-button>
            </b-form>
        </b-card>

        <b-modal
            id="forgotPasswordModal"
            ref="forgotPasswordModalRef"
            size="lg"
            title="Password recovery"
            hideFooter
            noEnforceFocus
            @shown="$refs.usernameEmailInput.focus(); usernameEmail=username"
        >
            <b-card class="no-hover">
                <b-form @submit.prevent="handleForgotPassword">
                    <h2 class="theme-h2 field-heading">
                        Username or email
                    </h2>
                    <b-input
                        ref="usernameEmailInput"
                        v-model="usernameEmail"
                        required
                        placeholder="Please enter your username or email"
                        class="theme-input multi-form"
                    />
                    <b-button
                        class="float-right orange-button"
                        type="submit"
                    >
                        <icon name="key"/>
                        Recover password
                    </b-button>
                    <b-button
                        class="red-button"
                        @click="$refs.forgotPasswordModalRef.hide()"
                    >
                        <icon name="times"/>
                        Cancel
                    </b-button>
                </b-form>
            </b-card>
        </b-modal>
    </div>
</template>

<script>
import authAPI from '@/api/auth.js'

import { mapGetters } from 'vuex'

export default {
    name: 'LoginForm',
    data () {
        return {
            usernameEmail: null,
            username: null,
            password: null,
        }
    },
    computed: {
        ...mapGetters({
            allowRegistration: 'instance/allowRegistration',
        }),
    },
    mounted () {
        if (this.$root.previousPage && this.$root.previousPage.name === 'SetPassword') {
            this.username = this.$root.previousPage.params.username
        }
    },
    methods: {
        handleForgotPassword () {
            authAPI.forgotPassword(this.usernameEmail, { responseSuccessToast: true, redirect: false })
                .then(() => { this.$refs.forgotPasswordModalRef.hide() })
        },
        handleLogin () {
            this.$store.dispatch('user/login', { username: this.username, password: this.password })
                .then(() => { this.$emit('handleAction') })
                .catch(() => { this.$toasted.error('Incorrect username or password.') })
        },
    },
}
</script>
