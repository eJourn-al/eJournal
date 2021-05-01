<template>
    <div>
        <b-form @submit.prevent="handleLogin()">
            <h2 class="theme-h2 field-heading">
                Username
            </h2>
            <b-input
                v-model="username"
                class="mb-2"
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
                type="password"
                required
                placeholder="Password"
                autocomplete="current-password"
            />
            <b-button
                class="float-right mt-2"
                type="submit"
            >
                <icon name="sign-in-alt"/>
                Log in
            </b-button>
            <b-button
                v-b-modal.forgotPasswordModal
                class="mt-2 orange-button mr-2"
            >
                <icon name="question"/>
                Forgot password
            </b-button>
            <b-button
                v-if="allowRegistration"
                :to="{ name: 'Register' }"
                class="mt-2"
            >
                <icon name="user-plus"/>
                Register
            </b-button>
        </b-form>

        <b-modal
            id="forgotPasswordModal"
            ref="forgotPasswordModalRef"
            size="lg"
            title="Password recovery"
            noEnforceFocus
            @shown="$refs.usernameEmailInput.focus(); usernameEmail = username"
        >
            <b-form
                id="forgotPasswordModalForm"
                @submit.prevent="handleForgotPassword"
            >
                <b-form-group
                    label="Username or email"
                    required
                >
                    <b-form-input
                        ref="usernameEmailInput"
                        v-model="usernameEmail"
                        placeholder="Please enter your username or email"
                        class="mb-2"
                        required
                    />
                </b-form-group>
            </b-form>

            <template #modal-footer="{ cancel }">
                <b-button
                    class="red-button mr-auto"
                    @click="cancel()"
                >
                    <icon name="times"/>
                    Cancel
                </b-button>
                <b-button
                    class="orange-button"
                    type="submit"
                    form="forgotPasswordModalForm"
                >
                    <icon name="key"/>
                    Recover password
                </b-button>
            </template>
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
