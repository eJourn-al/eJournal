<template>
    <content-single-column class="not-logged-in-page">
        <img
            class="not-logged-in-page-logo"
            src="ejournal-logo.svg"
        />
        <b-button
            class="round-border blue-button ml-auto mr-auto mb-2 d-block"
            :to="{ name: 'Home' }"
        >
            <icon name="arrow-left"/>
            Back to login
        </b-button>
        <b-card>
            <h2
                slot="header"
                class="theme-h2"
            >
                Register
            </h2>
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
                    class="mb-2"
                    required
                    placeholder="Email verification token"
                />
                <b-button
                    class="float-right mb-2 green-button"
                    type="submit"
                >
                    <icon name="save"/>
                    Submit
                </b-button>
            </b-form>
        </b-card>
        <custom-footer/>
    </content-single-column>
</template>

<script>
import contentSingleColumn from '@/components/columns/ContentSingleColumn.vue'
import customFooter from '@/components/assets/Footer.vue'
import registerUser from '@/components/account/RegisterUser.vue'
import userAPI from '@/api/user.js'

export default {
    name: 'Register',
    components: {
        contentSingleColumn,
        customFooter,
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
