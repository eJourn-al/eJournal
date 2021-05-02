<template>
    <wide-content>
        <bread-crumb/>
        <b-card noBody>
            <b-tabs
                card
                pills
                lazy
                @activate-tab="tabActivated"
            >
                <b-tab active>
                    <template slot="title">
                        <icon
                            name="edit"
                            class="shift-up-3"
                        />
                        Edit Instance
                    </template>
                    <edit-instance @dirty-changed="dirty = $event"/>
                </b-tab>
                <b-tab>
                    <template slot="title">
                        <icon
                            name="book"
                            class="shift-up-3"
                        />
                        Course Overview
                    </template>
                    <course-overview/>
                </b-tab>
                <b-tab>
                    <template slot="title">
                        <icon
                            name="users"
                            class="shift-up-3"
                        />
                        User Overview
                    </template>
                    <user-overview/>
                </b-tab>
                <b-tab>
                    <template slot="title">
                        <icon
                            name="user-plus"
                            class="shift-up-3"
                        />
                        Invite Users
                    </template>
                    <invite-users/>
                </b-tab>
                <b-tab>
                    <template slot="title">
                        <icon
                            name="cog"
                            class="shift-up-3"
                        />
                        LTI Settings
                    </template>
                    <lti-settings/>
                </b-tab>
            </b-tabs>
        </b-card>
    </wide-content>
</template>

<script>
import BreadCrumb from '@/components/assets/BreadCrumb.vue'
import CourseOverview from '@/components/admin/CourseOverview.vue'
import EditInstance from '@/components/admin/EditInstance.vue'
import InviteUsers from '@/components/admin/InviteUsers.vue'
import LtiSettings from '@/components/admin/LtiSettings.vue'
import UserOverview from '@/components/admin/UserOverview.vue'
import WideContent from '@/components/columns/WideContent.vue'

export default {
    name: 'AdminPanel',
    components: {
        WideContent,
        BreadCrumb,
        EditInstance,
        CourseOverview,
        UserOverview,
        InviteUsers,
        LtiSettings,
    },
    data () {
        return {
            dirty: false,
        }
    },
    methods: {
        safeToLeave () {
            if (this.dirty && !window.confirm('Unsaved changes will be lost if you leave. Do you wish to continue?')) {
                return false
            }
            return true
        },
        tabActivated (newTabIndex, prevTabIndex, bvEvent) {
            if (!this.safeToLeave()) {
                bvEvent.preventDefault()
            } else {
                this.dirty = false
            }
        },
    },
    beforeRouteLeave (to, from, next) {
        if (!this.safeToLeave()) {
            next(false)
        } else {
            next()
        }
    },
}
</script>
