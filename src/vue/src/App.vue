<template>
    <div id="app">
        <header-bar/>
        <router-view :key="$route.path"/>
        <feedback-section/>
    </div>
</template>

<script>
import headerBar from '@/Header.vue'
import feedbackSection from '@/FeedbackSection.vue'

export default {
    components: {
        headerBar,
        feedbackSection,
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
