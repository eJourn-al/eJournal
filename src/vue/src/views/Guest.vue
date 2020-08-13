<template>
    <content-single-column>
        <h1 class="theme-h1">
            <span>Welcome to {{ name ? name : 'eJournal' }}</span>
        </h1><br/>
        <h4 class="theme-h4 multi-form">
            <span>Let's get started</span>
        </h4>
        <login-form @handleAction="handleLoginSucces"/>
        <h4 class="theme-h4 multi-form mt-4">
            <span>About eJournal</span>
        </h4>
        <b-row>
            <b-col
                lg="5"
                class="mb-4"
            >
                <img
                    src="/journal-view.png"
                    class="screenshot round-border theme-shadow no-hover"
                />
            </b-col>
            <b-col lg="7">
                eJournal is a blended learning web application that provides an easy to manage graded journal system
                focused on education. Curious what eJournal has to offer for your education?
                <br/>
                <b-button
                    href="https://www.eJournal.app"
                    target="_blank"
                    class="mr-2 mt-4"
                >
                    <icon name="play"/>
                    Learn more
                </b-button>
                <b-button
                    href="mailto:contact@ejournal.app?subject=I%20would%20like%20to%20know%20more%20about%20eJournal!"
                    target="_blank"
                    class="change-button mt-4"
                >
                    <icon name="desktop"/>
                    Request a demo
                </b-button>
            </b-col>
        </b-row>
        <custom-footer style="clear:both"/>
    </content-single-column>
</template>
<script>
import contentSingleColumn from '@/components/columns/ContentSingleColumn.vue'
import customFooter from '@/components/assets/Footer.vue'
import loginForm from '@/components/account/LoginForm.vue'
import routerConstraints from '@/utils/constants/router_constraints.js'

import instanceAPI from '@/api/instance.js'

export default {
    name: 'Guest',
    components: {
        contentSingleColumn,
        customFooter,
        loginForm,
    },
    data () {
        return {
            name: null,
            username: '',
            password: '',
        }
    },
    created () {
        instanceAPI.get()
            .then((instance) => {
                this.name = instance.name
            })
    },
    methods: {
        handleLoginSucces () {
            if (this.$root.previousPage === null || this.$root.previousPage.name === null
                || this.$root.previousPage.name === 'Logout'
                || routerConstraints.PERMISSIONLESS_CONTENT.has(this.$root.previousPage.name)) {
                this.$router.push({ name: 'Home' })
            } else {
                this.$router.push({ name: this.$root.previousPage.name, params: this.$root.previousPage.params })
            }
        },
    },
}
</script>

<style lang="sass">
.screenshot
    width: 100%
    padding-top: 15px
    background-color: #444444
    background-image: url('../assets/images/window-controls.svg')
    background-repeat: no-repeat
    background-size: auto 10px
    background-position: 2px 2px
</style>
