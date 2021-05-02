<template>
    <content-single-column class="not-logged-in-page">
        <img
            class="not-logged-in-page-logo"
            src="ejournal-logo.svg"
        />
        <b-card>
            <template #header>
                <h2 class="theme-h2">
                    Log in
                </h2>
            </template>
            <login-form @handleAction="handleLoginSucces"/>
        </b-card>
        <custom-footer/>
    </content-single-column>
</template>

<script>
import contentSingleColumn from '@/components/columns/ContentSingleColumn.vue'
import customFooter from '@/components/assets/Footer.vue'
import loginForm from '@/components/account/LoginForm.vue'
import routerConstraints from '@/utils/constants/router_constraints.js'

export default {
    name: 'Login',
    components: {
        contentSingleColumn,
        customFooter,
        loginForm,
    },
    data () {
        return {
            username: '',
            password: '',
        }
    },
    methods: {
        handleLoginSucces () {
            if (this.$root.previousPage === null || this.$root.previousPage.name === null
                || routerConstraints.PERMISSIONLESS_CONTENT.has(this.$root.previousPage.name)) {
                this.$router.push({ name: 'Home' })
            } else {
                this.$router.push({ name: this.$root.previousPage.name, params: this.$root.previousPage.params })
            }
        },
    },
}
</script>
