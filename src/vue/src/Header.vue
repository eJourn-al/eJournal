<template>
    <!-- Section visible if user logged in -->
    <b-navbar
        v-if="loggedIn"
        id="header"
        class="theme-shadow no-hover"
        toggleable="md"
        type="dark"
        fixed="top"
    >
        <transition name="fade">
            <div
                v-if="showConnectionSpinner"
                class="spinner theme-shadow"
            >
                <icon
                    name="circle-notch"
                    spin
                    scale="1.1"
                />
            </div>
        </transition>
        <b-navbar-brand
            :to="{ name: 'Home' }"
            class="brand-name text-shadow"
        >
            <img
                src="/ejournal-logo-white.svg"
                class="theme-img"
            />
        </b-navbar-brand>

        <b-navbar-toggle
            class="ml-auto mr-auto"
            target="nav-collapse"
            aria-expanded="false"
            aria-controls="nav-collapse"
        >
            <span class="nav-collapse__icon nav-collapse__icon--open">
                <icon
                    class="collapse-icon"
                    name="caret-down"
                    scale="1.75"
                />
            </span>
            <span class="nav-collapse__icon nav-collapse__icon--close">
                <icon
                    class="collapse-icon"
                    name="caret-up"
                    scale="1.75"
                />
            </span>
        </b-navbar-toggle>

        <b-collapse
            id="nav-collapse"
            isNav
        >
            <b-navbar-nav class="mr-auto">
                <b-nav-item :to="{ name : 'Home' }">
                    <icon name="home"/>
                    Courses
                </b-nav-item>
                <b-nav-item :to="{ name : 'AssignmentsOverview' }">
                    <icon name="edit"/>
                    Assignments
                </b-nav-item>
            </b-navbar-nav>
        </b-collapse>

        <b-navbar-nav class="ml-auto">
            <b-nav-dropdown
                id="nav-dropdown-options"
                noCaret
                right
            >
                <div
                    slot="button-content"
                    class="profile-picture-container"
                >
                    <img
                        :src="profileImg"
                        class="theme-img profile-picture-sm"
                    />
                </div>
                <b-button
                    :to="{ name: 'Profile' }"
                    class="mb-1"
                >
                    <icon name="user"/>
                    &nbsp;Profile
                </b-button>
                <b-button :to="{ name: 'Logout' }">
                    <icon name="sign-out-alt"/>
                    Log out
                </b-button>
            </b-nav-dropdown>
        </b-navbar-nav>
    </b-navbar>

    <!-- Section visible if user logged out -->
    <b-navbar
        v-else
        id="header"
        class="theme-shadow no-hover"
        toggleable="md"
        type="dark"
        fixed="top"
    >
        <transition name="fade">
            <div
                v-if="showConnectionSpinner"
                class="spinner theme-shadow"
            >
                <icon
                    name="circle-notch"
                    spin
                    scale="1.3"
                />
            </div>
        </transition>
        <b-navbar-brand
            :to="{ name: 'Guest' }"
            class="brand-name"
        >
            <img
                src="/ejournal-logo-white.svg"
                class="theme-img"
            />
        </b-navbar-brand>

        <b-navbar-nav
            v-if="$route.name !== 'LtiLogin'"
            class="ml-auto"
        >
            <b-nav-dropdown
                id="nav-dropdown-options"
                ref="loginDropdown"
                right
                noCaret
            >
                <div
                    slot="button-content"
                    class="profile-picture-container bg-white d-flex justify-content-center align-items-center"
                >
                    <icon
                        name="user"
                        class="fill-dark-blue"
                        scale="2"
                    />
                </div>
                <b-button
                    v-if="allowRegistration"
                    :to="{ name: 'Register' }"
                    class="mb-1"
                >
                    <icon name="user-plus"/>
                    Register
                </b-button>
                <b-button :to="{ name: 'Login' }">
                    <icon name="sign-in-alt"/>
                    Log in
                </b-button>
            </b-nav-dropdown>
        </b-navbar-nav>
    </b-navbar>
</template>

<script>
import { mapGetters } from 'vuex'

import instanceAPI from '@/api/instance.js'

export default {
    data () {
        return {
            defaultProfileImg: '/unknown-profile.png',
            allowRegistration: null,
        }
    },
    computed: {
        ...mapGetters({
            loggedIn: 'user/loggedIn',
            profileImg: 'user/profilePicture',
            showConnectionSpinner: 'connection/showConnectionSpinner',
        }),
    },
    created () {
        instanceAPI.get()
            .then((instance) => {
                this.allowRegistration = instance.allow_standalone_registration
            })
    },
}
</script>

<style lang="sass">
@import '~sass/modules/colors.sass'
@import '~sass/modules/breakpoints.sass'
@import '~sass/partials/shadows.sass'

#header
    background-color: $theme-dark-blue
    color: white
    font-family: 'Roboto Condensed', sans-serif
    font-size: 1.3em
    height: 70px
    border-radius: 0px 0px 5px 5px !important
    .nav-link
        > svg
            fill: grey !important
        &:hover
            > svg
                fill: $theme-medium-grey !important
        &.router-link-active
            color: white
            > svg
                fill: $theme-orange !important
    .brand-name
        img
            height: 30px
    .navbar-toggler
        .collapse-icon
            fill: white !important
        @include md-max
            position: absolute
            left: 50%
            right: 50%
            top: 15px
            transform: translateX(-50%)
            border-radius: 50% !important
    /* Handles rotation of the arrow icon. */
    [aria-expanded="false"] .nav-collapse__icon--open
        display: block

    [aria-expanded="false"] .nav-collapse__icon--close
        display: none

    [aria-expanded="true"] .nav-collapse__icon--open
        display: none

    [aria-expanded="true"] .nav-collapse__icon--close
        display: block
    @include md-max
        min-height: 70px
        height: auto

#nav-dropdown-options
    .profile-picture-container
        border-radius: 50% !important
        width: 50px
        height: 50px
        @include md-max
            position: absolute
            top: 10px
            right: 10px
    a
        padding: 0px !important
    a.btn
        padding: 0.375rem 0.75rem !important
        width: 100%
    @include md-max
        position: absolute
        top: 0px
        right: 0px
        width: auto

        a.nav-link
            text-align: right !important

.dropdown-menu
    @extend .theme-shadow
    background: $theme-dark-blue !important
    border: none !important
    border-radius: 0px 0px 5px 5px !important
    padding: 5px 5px
    margin-top: 10px
    .btn
        justify-content: left
        svg
            margin-left: 0px
    @include md-max
        margin-top: 70px

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
