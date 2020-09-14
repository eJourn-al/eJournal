<template>
    <b-alert
        id="code-version-alert"
        :show="show"
        class="cursor-pointer unselectable"
        @click.native="beginRefreshForNewVersion"
    >
        eJournal received an update 🎉, click to refresh.
    </b-alert>
</template>

<script>
export default {
    computed: {
        show () {
            const backendCodeVersionDiffers = (
                this.$store.getters['user/backendCodeVersion']
                && this.$store.getters['user/backendCodeVersion'] !== CustomEnv.CODE_VERSION)

            const alreadyRefreshed = (
                this.$store.getters['user/refreshedForCodeVersion'] === this.$store.getters['user/backendCodeVersion'])

            return backendCodeVersionDiffers && !alreadyRefreshed
        },
    },
    methods: {
        beginRefreshForNewVersion () {
            this.$store.commit('user/SET_REFRESHED_FOR_CODE_VERSION', this.$store.getters['user/backendCodeVersion'])
            this.$store.commit('user/SET_REFRESH_TRIGGERED_DUE_TO_CODE_VERSION', true)
            window.location.reload(true)
        },
    },
}
</script>

<style lang="sass">
@import '~sass/modules/colors.sass'

#code-version-alert
    position: absolute
    margin: 2px
    bottom: 0

    &:hover
        background-color: $theme-green !important
        border-color: $theme-green !important
        color: white !important
</style>
