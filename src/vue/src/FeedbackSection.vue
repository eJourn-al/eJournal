<template>
    <div
        v-if="loggedIn"
        class="feedback-wrapper"
    >
        <div
            class="theme-shadow feedback-button"
            @click="showModal('feedbackModal')"
        >
            <icon
                name="life-ring"
                scale="1"
                class="shift-up-2"
            />
            Support
        </div>

        <b-modal
            ref="feedbackModal"
            size="lg"
            title="Technical support"
            hideFooter
            noEnforceFocus
        >
            <feedback @feedbackSent="hideModal('feedbackModal')"/>
        </b-modal>
    </div>
</template>

<script>
import feedback from '@/components/assets/Feedback.vue'

import { mapGetters } from 'vuex'

export default {
    components: {
        feedback,
    },
    computed: {
        ...mapGetters({
            loggedIn: 'user/loggedIn',
            profileImg: 'user/profilePicture',
        }),
    },
    methods: {
        showModal (ref) {
            this.$refs[ref].show()
        },
        hideModal (ref) {
            this.$refs[ref].hide()
        },
    },
}
</script>

<style lang="sass">
@import '~sass/modules/colors.sass'
@import '~sass/modules/breakpoints.sass'

.feedback-wrapper
    position: fixed
    bottom: 0px
    z-index: 1200
    .feedback-button
        font-family: 'Roboto Condensed', sans-serif
        cursor: pointer
        padding: 2px 10px 2px 10px
        position: fixed
        bottom: 0px
        right: 150px
        background-color: white
        border: 2px solid $theme-dark-grey
        border-bottom-width: 0px
        border-radius: 10px 10px 0px 0px !important
        &, svg
            color: $theme-dark-blue
            transition: all 0.3s cubic-bezier(.25,.8,.25,1) !important
        &:hover
            background-color: $theme-dark-blue
            &, svg
                color: white
</style>
