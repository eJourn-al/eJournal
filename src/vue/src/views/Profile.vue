<template>
    <wide-content>
        <b-button
            class="grey-button d-inline-block float-right mb-2"
            variant="link"
            @click="logOut"
        >
            <icon name="sign-out-alt"/>
            Log out
        </b-button>
        <bread-crumb/>
        <b-card noBody>
            <b-tabs
                card
                pills
                lazy
            >
                <b-tab>
                    <template slot="title">
                        <icon
                            name="user"
                            class="shift-up-3"
                        />
                        Details
                    </template>
                    <profile-data/>
                </b-tab>
                <b-tab>
                    <template slot="title">
                        <icon
                            name="envelope"
                            class="shift-up-3"
                        />
                        Email notifications
                    </template>
                    <notification-settings/>
                </b-tab>
                <b-tab v-if="$root.canGradeForSomeCourse()">
                    <template slot="title">
                        <icon
                            name="edit"
                            class="shift-up-3"
                        />
                        Grading
                    </template>
                    <grading-settings/>
                </b-tab>
                <b-tab>
                    <template slot="title">
                        <icon
                            name="key"
                            class="shift-up-3"
                        />
                        Password
                    </template>
                    <password-settings/>
                </b-tab>
            </b-tabs>
        </b-card>
    </wide-content>
</template>

<script>
import WideContent from '@/components/columns/WideContent.vue'
import breadCrumb from '@/components/assets/BreadCrumb.vue'
import gradingSettings from '@/components/profile/GradingSettings.vue'
import notificationSettings from '@/components/profile/NotificationSettings.vue'
import passwordSettings from '@/components/profile/PasswordSettings.vue'
import profileData from '@/components/profile/ProfileData.vue'

export default {
    name: 'Profile',
    components: {
        WideContent,
        breadCrumb,
        gradingSettings,
        profileData,
        notificationSettings,
        passwordSettings,
    },
    methods: {
        logOut () {
            this.$store.dispatch('user/logout')
            this.$router.push({ name: 'Login' })
        },
    },
}
</script>
