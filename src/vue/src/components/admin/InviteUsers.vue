<template>
    <div>
        Invite new users to eJournal by entering their details in the fields below.
        Invited users will receive an email to activate their account and set up a password.
        <b-table-simple
            responsive
            striped
            noSortReset
            sortBy="name"
            class="mt-2 mb-0 table-striped"
        >
            <b-thead>
                <b-tr class="text-align-left">
                    <b-th>
                        Name
                    </b-th>
                    <b-th>
                        Username
                    </b-th>
                    <b-th>
                        Email
                    </b-th>
                    <b-th>
                        Is teacher
                    </b-th>
                    <b-th/>
                </b-tr>
            </b-thead>
            <b-tbody>
                <b-tr
                    v-for="(user, index) in usersToInvite"
                    :key="index"
                >
                    <b-td>
                        <input
                            v-model="user.full_name"
                            type="text"
                            class="theme-input"
                            placeholder="Name"
                        />
                    </b-td>
                    <b-td>
                        <input
                            v-model="user.username"
                            type="text"
                            class="theme-input"
                            placeholder="Username"
                        />
                    </b-td>
                    <b-td>
                        <input
                            v-model="user.email"
                            type="text"
                            class="theme-input"
                            placeholder="Email"
                        />
                    </b-td>
                    <b-td>
                        <b-form-checkbox
                            v-model="user.is_teacher"
                        />
                    </b-td>
                    <b-td>
                        <icon
                            name="trash"
                            class="trash-icon"
                            @click.native="removeRow(user)"
                        />
                    </b-td>
                </b-tr>
            </b-tbody>
        </b-table-simple>
        <span
            class="text-grey ml-3 cursor-pointer unselectable darken-on-hover"
            @click="addRow"
        >
            <icon
                name="plus"
                class="shift-up-3"
            />
            Add row
        </span>
        <b-card
            v-if="errorLogs"
            class="mt-2 mb-2 no-hover"
        >
            <template v-if="errorLogs.duplicate_usernames">
                <b class="text-red">The following usernames occur multiple times:</b>
                <ul>
                    <li
                        v-for="username in errorLogs.duplicate_usernames"
                        :key="username"
                    >
                        {{ username }}
                    </li>
                </ul>
            </template>
            <template v-if="errorLogs.duplicate_emails">
                <b class="text-red">The following email addresses occur multiple times:</b>
                <ul>
                    <li
                        v-for="email in errorLogs.duplicate_emails"
                        :key="email"
                    >
                        {{ email }}
                    </li>
                </ul>
            </template>
            <template v-if="errorLogs.existing_usernames">
                <b class="text-red">The following usernames already belong to existing users:</b>
                <ul>
                    <li
                        v-for="username in errorLogs.existing_usernames"
                        :key="username"
                    >
                        {{ username }}
                    </li>
                </ul>
            </template>
            <template v-if="errorLogs.existing_emails">
                <b class="text-red">The following email addresses already belong to existing users:</b>
                <ul>
                    <li
                        v-for="email in errorLogs.existing_emails"
                        :key="email"
                    >
                        {{ email }}
                    </li>
                </ul>
            </template>
        </b-card>
        <b-button
            :class="{
                'input-disabled': requestInFlight || usersToInviteFiltered.length === 0,
            }"
            class="green-button float-right mb-2"
            @click="inviteUsers"
        >
            <icon name="paper-plane"/>
            Send Invites
        </b-button>
    </div>
</template>

<script>
import adminAPI from '@/api/admin.js'

export default {
    data () {
        return {
            usersToInvite: [{
                full_name: null,
                username: null,
                email: null,
                is_teacher: false,
            }],
            errorLogs: null,
            requestInFlight: false,
        }
    },
    computed: {
        usersToInviteFiltered () {
            // Filter fully empty rows.
            return this.usersToInvite.filter(user => !(!user.full_name && !user.username && !user.email))
        },
    },
    methods: {
        inviteUsers () {
            this.requestInFlight = true
            adminAPI.inviteUsers({
                users: this.usersToInviteFiltered,
            }, {
                customSuccessToast: 'Successfully invited users.',
                customErrorToast: 'Some user details were invalid. No invites sent.',
            })
                .then(() => {
                    this.requestInFlight = false
                    this.errorLogs = null
                    this.usersToInvite = [{
                        full_name: null,
                        username: null,
                        email: null,
                        is_teacher: false,
                    }]
                })
                .catch((error) => {
                    if (typeof error.response.data.description === 'object') {
                        this.errorLogs = error.response.data.description
                    } else {
                        this.$toasted.error(error.response.data.description)
                    }
                    this.requestInFlight = false
                })
        },
        addRow () {
            this.usersToInvite.push({
                full_name: null,
                username: null,
                email: null,
                is_teacher: false,
            })
        },
        removeRow (user) {
            this.usersToInvite.pop(user)
            if (this.usersToInvite.length === 0) {
                this.addRow()
            }
        },
    },
}
</script>
