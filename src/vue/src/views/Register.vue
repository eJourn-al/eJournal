<template>
    <content-single-column>
        <h1 class="theme-h1">
            <span>
                Register
            </span>
        </h1>
        <b-card
            class="no-hover"
        >
            <register-user
                v-if="!accountCreated"
                @handleAction="accountCreated=true"
            />
            <b-form
                v-else
                @submit.prevent="verifyEmail"
            >
                <h2 class="theme-h2 field-heading">
                    Email verification token
                </h2>
                <b-input
                    v-model="emailVerificationToken"
                    class="multi-form theme-input"
                    required
                    placeholder="Email verification token"
                />
                <b-button
                    class="float-right multi-form green-button"
                    type="submit"
                >
                    <icon name="save"/>
                    Submit
                </b-button>
            </b-form>
        </b-card>
    </content-single-column>
</template>

<script>
import contentSingleColumn from '@/components/columns/ContentSingleColumn.vue'
import registerUser from '@/components/account/RegisterUser.vue'
import userAPI from '@/api/user.js'

export default {
    name: 'Register',
    components: {
        contentSingleColumn,
        registerUser,
    },
    props: ['username', 'token'],
    data () {
        return {
            accountCreated: false,
            emailVerificationToken: null,
        }
    },
    methods: {
        verifyEmail () {
            userAPI.verifyEmail(
                this.$store.getters['user/username'],
                this.emailVerificationToken,
                { responseSuccessToast: true },
            )
                .then(() => {
                    this.$store.commit('user/EMAIL_VERIFIED')
                    this.$router.push({ name: 'Home' })
                })
        },
    },
}
</script>
