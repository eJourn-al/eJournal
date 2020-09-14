<template>
    <div id="app">
        <header-bar/>
        <router-view :key="$route.path"/>
        <feedback-section/>
        <code-version-alert/>
    </div>
</template>

<script>
import headerBar from '@/Header.vue'
import feedbackSection from '@/FeedbackSection.vue'
import codeVersionAlert from '@/components/assets/CodeVersionAlert.vue'

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
    overflow-x: hidden
    padding-top: 70px
    min-height: 100%
</style>
