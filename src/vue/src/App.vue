<template>
    <div id="app">
        <header-bar/>
        <router-view :key="$route.path"/>
        <feedback-section/>
        <code-version-alert/>
    </div>
</template>

<script>
import codeVersionAlert from '@/components/assets/CodeVersionAlert.vue'
import feedbackSection from '@/FeedbackSection.vue'
import headerBar from '@/Header.vue'

export default {
    components: {
        headerBar,
        feedbackSection,
        codeVersionAlert,
    },
    mounted () {
        /* Code version mismatch triggered refresh without cache, repopulate store. */
        if (this.$store.getters['user/refreshTriggerDueToCodeVersion']) {
            this.$store.dispatch('user/populateStore')
            this.$store.commit('user/SET_REFRESH_TRIGGERED_DUE_TO_CODE_VERSION', false)
        }
    },
}
</script>

<style lang="sass">
@import '~sass/global.sass'
@import '~sass/modules/breakpoints.sass'

#app
    margin: auto
    width: 100%
    max-width: $max-app-width
    overflow-x: hidden
    padding-top: $header-height
    min-height: 100%
</style>
