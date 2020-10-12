<template>
    <div>
        <b-form
            @submit.prevent="onSubmit"
            @reset.prevent="onReset"
        >
            <h2
                v-if="!lti"
                class="theme-h2 field-heading required"
            >
                Username
            </h2>
            <b-input
                v-if="!lti"
                v-model="form.username"
                class="multi-form theme-input"
                placeholder="Username"
                maxlength="30"
                required
            />
            <h2
                v-if="!lti"
                class="theme-h2 field-heading required"
            >
                Full name
            </h2>
            <b-input
                v-if="!lti"
                v-model="form.fullName"
                class="multi-form theme-input"
                placeholder="Full name"
                maxlength="200"
                required
            />
            <h2 class="theme-h2 field-heading required">
                New password
                <tooltip
                    tip="Should contain at least 8 characters, a capital letter and a special character"
                />
            </h2>
            <b-input
                v-model="form.password"
                class="multi-form theme-input"
                type="password"
                placeholder="Password"
                required
            />
            <h2 class="theme-h2 field-heading required">
                Repeat new password
            </h2>
            <b-input
                v-model="form.password2"
                class="multi-form theme-input"
                type="password"
                placeholder="Repeat password"
                required
            />
            <h2
                v-if="!lti"
                class="theme-h2 field-heading required"
            >
                Email
            </h2>
            <b-input
                v-if="!lti"
                v-model="form.email"
                class="multi-form theme-input"
                placeholder="Email"
                required
            />
            <b-button
                class="float-left change-button multi-form"
                type="reset"
            >
                <icon name="undo"/>
                Reset
            </b-button>
            <b-button
                class="float-right multi-form"
                :class="{ 'input-disabled': saveRequestInFlight }"
                type="submit"
            >
                <icon name="user-plus"/>
                Create account
            </b-button>
        </b-form>
    </div>
</template>

<script>
import tooltip from '@/components/assets/Tooltip.vue'

import authAPI from '@/api/auth.js'
import validation from '@/utils/validation.js'

export default {
    name: 'RegisterUser',
    components: {
        tooltip,
    },
    props: ['lti'],
    data () {
        return {
            form: {
                username: '',
                password: '',
                password2: '',
                fullName: '',
                email: '',
                ltiJWT: '',
            },
            saveRequestInFlight: false,
        }
    },
    methods: {
        onSubmit () {
            this.saveRequestInFlight = true
            if (this.lti) {
                this.form.username = this.lti.username
                this.form.ltiJWT = this.lti.ltiJWT
            }

            if (validation.validatePassword(this.form.password, this.form.password2)
                && (this.lti || validation.validateEmail(this.form.email))) {
                authAPI.register(
                    this.form.username,
                    this.form.password,
                    this.form.fullName,
                    this.form.email,
                    this.form.ltiJWT,
                    {
                        customSuccessToast: this.lti ? '' : `Registration successful! Please follow the instructions
                        sent to ${this.form.email} to confirm your email address.`,
                    })
                    .then(() => {
                        this.$store.dispatch(
                            'user/login',
                            { username: this.form.username, password: this.form.password },
                        )
                            .then(() => {
                                this.$emit('handleAction')
                                this.saveRequestInFlight = false
                            })
                            .catch(() => {
                                this.saveRequestInFlight = false
                                this.$toasted.error('Error logging in with your newly created account, please contact '
                                + 'a system administrator or try registering again.')
                            })
                    })
                    .catch(() => {
                        this.saveRequestInFlight = false
                    })
            } else {
                this.saveRequestInFlight = false
            }
        },
        onReset () {
            this.form.username = ''
            this.form.password = ''
            this.form.password2 = ''
            this.form.fullName = ''
            this.form.email = ''
        },
    },
}
</script>
