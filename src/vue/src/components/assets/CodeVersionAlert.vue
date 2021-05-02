<template>
    <b-alert
        id="code-version-alert"
        :show="show"
        class="cursor-pointer unselectable"
        @click.native="beginRefreshForNewVersion"
    >
        eJournal received an update 🎉, click <b>here</b> to reload
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
#code-version-alert
    position: fixed
    margin: 2px
    bottom: 10px
    left: 10px
</style>
