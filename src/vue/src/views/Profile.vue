<template>
    <content-single-column>
        <bread-crumb/>
        <profile-data ref="profileData"/>
        <notification-card/>
        <grading-card v-if="$root.canGradeForSomeCourse"/>
        <h4 class="theme-h4 mb-2 mt-4">
            <span>Password</span>
        </h4>
        <password-card ref="passData"/>
        <custom-footer/>
    </content-single-column>
</template>

<script>
import contentSingleColumn from '@/components/columns/ContentSingleColumn.vue'
import customFooter from '@/components/assets/Footer.vue'
import gradingCard from '@/components/profile/GradingCard.vue'
import profileData from '@/components/profile/ProfileData.vue'
import notificationCard from '@/components/profile/NotificationCard.vue'
import passwordCard from '@/components/profile/PasswordCard.vue'
import breadCrumb from '@/components/assets/BreadCrumb.vue'

export default {
    name: 'Profile',
    components: {
        contentSingleColumn,
        customFooter,
        breadCrumb,
        gradingCard,
        profileData,
        notificationCard,
        passwordCard,
    },
    beforeRouteLeave (to, from, next) {
        if ((this.$refs.profileData.isChanged() || this.$refs.passData.isChanged())
            && !window.confirm('Unsaved changes will be lost if you leave. Do you wish to continue?')) {
            next(false)
            return
        }

        next()
    },
}
</script>
