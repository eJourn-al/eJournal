<template>
    <div>
        <b-input-group>
            <b-input
                v-model="email"
                :readonly="$store.getters['user/verifiedEmail']"
                class="no-right-radius"
                type="text"
            />
            <b-button
                slot="append"
                v-b-tooltip:hover="(showEmailValidationInput) ? 'Enter the email verification token below' :
                    'Click to verify your email'"
                :disabled="$store.getters['user/verifiedEmail'] || showEmailValidationInput"
                @click="requestEmailVerification"
            >
                <icon
                    v-if="!$store.getters['user/verifiedEmail']"
                    :name="(showEmailValidationInput) ? 'check' : 'paper-plane'"
                />
                <icon
                    v-if="$store.getters['user/verifiedEmail']"
                    v-b-tooltip:hover="'Your email is verified!'"
                    name="check"
                    class="checked-icon"
                />
            </b-button>
        </b-input-group>

        <b-input-group
            v-if="!$store.getters['user/verifiedEmail'] && showEmailValidationInput"
            class="mt-2"
        >
            <b-input
                v-model="emailVerificationToken"
                class="no-right-radius"
                required
                placeholder="Enter the email verification token"
            />
            <b-button
                slot="append"
                @click="verifyEmail"
            >
                <icon
                    v-b-tooltip:hover="'Validate verification token'"
                    name="paper-plane"
                />
            </b-button>
        </b-input-group>
    </div>
</template>

<script>
import userAPI from '@/api/user.js'

export default {
    data () {
        return {
            showEmailValidationInput: false,
            emailVerificationToken: null,
            emailVerificationTokenMessage: null,
        }
    },
    computed: {
        email: {
            get () {
                return this.$store.getters['user/email']
            },
            set (value) {
                this.$store.commit('user/SET_EMAIL', value)
            },
        },
    },
    methods: {
        requestEmailVerification () {
            if (!this.showEmailValidationInput) {
                userAPI.requestEmailVerification(this.email, { responseSuccessToast: true })
                    .then(() => { this.showEmailValidationInput = true })
            }
        },
        verifyEmail () {
            userAPI.verifyEmail(
                this.$store.getters['user/username'],
                this.emailVerificationToken,
                { responseSuccessToast: true },
            )
                .then(() => {
                    this.$store.commit('user/EMAIL_VERIFIED')
                    this.showEmailValidationInput = false
                })
                .catch(() => { this.emailVerificationTokenMessage = 'Invalid token' })
        },
    },
}
</script>
