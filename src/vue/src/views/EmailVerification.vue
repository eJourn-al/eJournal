<template>
    <content-single-column>
        <h1 class="theme-h1">
            <span>Email Verification</span>
        </h1>
        <b-card class="no-hover">
            <div class="center-content">
                <h2 class="theme-h2 center-content">
                    Verifying
                </h2><br/>
                <icon
                    name="circle-notch"
                    pulse
                    scale="1.5"
                />
            </div>
        </b-card>
    </content-single-column>
</template>

<script>
import contentSingleColumn from '@/components/columns/ContentSingleColumn.vue'
import userAPI from '@/api/user.js'

export default {
    name: 'EmailVerification',
    components: {
        contentSingleColumn,
    },
    props: ['username', 'token'],
    mounted () {
        userAPI.verifyEmail(this.username, this.token, { responseSuccessToast: true })
            .then(() => {
                this.$store.commit('user/EMAIL_VERIFIED')
                this.$router.push({ name: 'Home' })
            })
    },
}
</script>
