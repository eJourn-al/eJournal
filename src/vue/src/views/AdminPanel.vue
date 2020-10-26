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
import UserOverview from '@/components/admin/UserOverview.vue'
import InviteUsers from '@/components/admin/InviteUsers.vue'


export default {
    name: 'AdminPanel',
    components: {
        WideContent,
        BreadCrumb,
        UserOverview,
        InviteUsers,
    },
    data () {
        return {
            errorLogs: '',
            requestInFlight: false,
        }
    },
}
</script>
