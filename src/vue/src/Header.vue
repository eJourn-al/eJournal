<template>
    <!-- Section visible if user logged in -->
    <b-navbar
        v-if="loggedIn"
        id="header"
        class="shadow-sm"
        fixed="top"
        variant="dark"
    >
        <transition name="fade">
            <div
                v-if="showConnectionSpinner"
                class="spinner"
            >
                <icon
                    name="circle-notch"
                    spin
                    scale="1.1"
                />
            </div>
        </transition>
        <icon
            v-b-toggle.nav-sidebar
            class="ml-1 mr-4 nav-sidebar-button"
            name="bars"
        />
        <b-navbar-brand
            :to="{ name: 'Home' }"
            class="brand-name"
        >
            <img
                src="/ejournal-logo-white.svg"
                class="unselectable"
            />
        </b-navbar-brand>

        <b-sidebar
            id="nav-sidebar"
            backdrop-variant="dark"
            backdrop
            shadow
        >
            <template #header>
                <icon
                    v-b-toggle.nav-sidebar
                    class="ml-1 mr-4 cursor-pointer text-white"
                    name="bars"
                />
                <b-navbar-brand class="brand-name">
                    <img
                        src="/ejournal-logo-white.svg"
                        class="unselectable"
                    />
                </b-navbar-brand>
            </template>
            <b-nav
                isNav
                vertical
            >
                <b-nav-item :to="{ name : 'Home' }">
                    <icon
                        name="book"
                        class="shift-up-3 mr-1 ml-1"
                    />
                    Courses
                </b-nav-item>
                <b-nav-item :to="{ name : 'AssignmentsOverview' }">
                    <icon
                        name="edit"
                        class="shift-up-3 mr-1 ml-1"
                    />
                    Assignments
                </b-nav-item>
                <b-nav-item
                    v-if="$store.getters['user/isSuperuser']"
                    :to="{ name : 'AdminPanel' }"
                >
                    <icon
                        name="user-shield"
                        class="shift-up-3 mr-1 ml-1"
                    />
                    Admin Panel
                </b-nav-item>
                <b-nav-item
                    :to="{ name : 'Profile' }"
                >
                    <icon
                        name="user"
                        class="shift-up-3 mr-1 ml-1"
                    />
                    Profile
                </b-nav-item>
                <b-nav-item
                    @click="logOut"
                >
                    <icon
                        name="sign-out-alt"
                        class="shift-up-3 mr-1 ml-1"
                    />
                    Log out
                </b-nav-item>
            </b-nav>
            <custom-footer slot="footer"/>
        </b-sidebar>
        <b-link :to="{ name: 'Profile' }">
            <img
                :src="profileImg"
                class="profile-picture"
            />
        </b-link>
    </b-navbar>
</template>

<script>
import { mapGetters } from 'vuex'
import customFooter from '@/components/assets/Footer.vue'

export default {
    components: {
        customFooter,
    },
    data () {
        return {
            defaultProfileImg: '/unknown-profile.png',
        }
    },
    computed: {
        ...mapGetters({
            loggedIn: 'user/loggedIn',
            profileImg: 'user/profilePicture',
            showConnectionSpinner: 'connection/showConnectionSpinner',
            allowRegistration: 'instance/allowRegistration',
        }),
    },
    methods: {
        logOut () {
            this.$store.dispatch('user/logout')
            this.$router.push({ name: 'Login' })
        },
    },
}
</script>

<style lang="sass">
#header
    padding: 0px 10px
    height: $header-height
    background-color: $theme-dark-blue !important
    .nav-sidebar-button
        color: white
        &:hover
            cursor: pointer
            color: $theme-light-grey
    .brand-name
        padding: 0px
        img
            height: calc(#{$header-height} - 20px)
            margin-top: -5px
    #nav-sidebar
        .b-sidebar-header
            background-color: $theme-dark-blue
        .b-sidebar-header, .b-sidebar-body
            padding: 8px 10px
        .nav-link
            color: grey
            background-color: $theme-light-grey
            border-radius: 5px
            margin-bottom: 8px
            &:hover
                background-color: $theme-medium-grey
            &.router-link-active
                color: $text-color
                font-weight: bold
                > svg
                    fill: $theme-blue !important
        .b-sidebar-footer
            margin: 0px
            background-color: $theme-light-grey
    .profile-picture
        border-radius: 8px
        border-width: 0px
        position: fixed
        right: 10px
        top: 10px
        overflow: hidden
        width: calc(#{$header-height} - 20px)
        height: calc(#{$header-height} - 20px)
        &:hover
            opacity: 0.9

    .spinner
        background: white
        color: $theme-dark-blue
        position: fixed
        bottom: 0px
        left: 0px
        width: 1.5em
        height: 1.5em
        border-radius: 0px 5px 0px 0px !important
        display: flex
        align-items: center
        justify-content: center

</style>
