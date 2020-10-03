<template>
    <wide-content>
        <bread-crumb/>
        <b-card
            class="no-hover no-left-border"
            noBody
        >
            <b-tabs
                card
                pills
                lazy
            >
                <b-tab>
                    <template slot="title">
                        <icon
                            name="edit"
                            class="shift-up-3"
                        />
                        Edit Instance
                    </template>
                    <edit-instance/>
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
                <b-tab active>
                    <template slot="title">
                        <icon
                            name="user-plus"
                            class="shift-up-3"
                        />
                        Invite Users
                    </template>
                    <invite-users/>
                </b-tab>
            </b-tabs>
        </b-card>
    </wide-content>
</template>

<script>
import WideContent from '@/components/columns/WideContent.vue'
import BreadCrumb from '@/components/assets/BreadCrumb.vue'
import EditInstance from '@/components/admin/EditInstance.vue'
import UserOverview from '@/components/admin/UserOverview.vue'
import InviteUsers from '@/components/admin/InviteUsers.vue'


// import courseAPI from '@/api/course.js'
import adminAPI from '@/api/admin.js'

export default {
    name: 'AdminPanel',
    components: {
        WideContent,
        BreadCrumb,
        EditInstance,
        UserOverview,
        InviteUsers,
    },
    data () {
        return {
            errorLogs: '',
            requestInFlight: false,
        }
    },
    methods: {
        inviteUsers () {
            this.requestInFlight = true
            adminAPI.inviteUsers({
                users: [
                    {
                        full_name: 'Engel Hamer',
                        username: 'hamertje',
                        email: 'engelhamer@gmail.com',
                    },
                ],
            }, {
                customSuccessToast: 'Successfully invited users.',
                customErrorToast: 'Some user details were invalid. No invites sent.',
            })
                .then(() => { this.requestInFlight = true })
                .catch((error) => {
                    this.errorLogs = error.response.data.description
                    this.requestInFlight = true
                })
        },
    },
}
</script>
