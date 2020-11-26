<template>
    <div>
        Invite new users to eJournal by entering their details in the fields below.
        Invited users will receive an email to activate their account and set up a password.
        <b-table-simple
            responsive
            striped
            noSortReset
            sortBy="name"
            class="mt-2 mb-2 table-striped"
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
                    <b-td class="align-middle">
                        <input
                            v-model="user.full_name"
                            type="text"
                            class="theme-input"
                            placeholder="Name"
                        />
                    </b-td>
                    <b-td class="align-middle">
                        <input
                            v-model="user.username"
                            type="text"
                            class="theme-input"
                            placeholder="Username"
                        />
                    </b-td>
                    <b-td class="align-middle">
                        <input
                            v-model="user.email"
                            type="text"
                            class="theme-input"
                            placeholder="Email"
                        />
                    </b-td>
                    <b-td class="align-middle">
                        <b-form-checkbox
                            v-model="user.is_teacher"
                        />
                    </b-td>
                    <b-td class="align-middle">
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
            Add Row
        </span>
        <span
            class="text-grey ml-3 cursor-pointer unselectable darken-on-hover"
            @click="$refs['invite-user-file-upload-modal'].show()"
        >
            <icon
                name="file-import"
                class="shift-up-3"
            />
            Import Spreadsheet
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

        <b-modal
            ref="invite-user-file-upload-modal"
            size="lg"
            hideFooter
            noEnforceFocus
            title="Import users"
        >
            <b-card class="no-hover">
                <h2 class="theme-h2 mb-2">
                    Import users to invite from a spreadsheet
                </h2>
                Upload a spreadsheet to import new users to eJournal. Please adhere to the following format, with each
                new user on a new row. <b>Note:</b> no headers shall be present in the file.


                <table
                    class="mt-2 mb-2 full-width border"
                >
                    <thead>
                        <tr class="text-align-left border">
                            <th class="p-1 border">
                                Name
                            </th>
                            <th class="p-1 border">
                                Username
                            </th>
                            <th class="p-1 border">
                                Email
                            </th>
                            <th class="p-1 border">
                                Is teacher
                            </th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td class="p-1 border">
                                John Doe
                            </td>
                            <td class="p-1 border">
                                user1
                            </td>
                            <td class="p-1 border">
                                test@example.com
                            </td>
                            <td class="p-1 border">
                                1
                            </td>
                        </tr>
                        <tr>
                            <td class="p-1 border">
                                Jane Doe
                            </td>
                            <td class="p-1 border">
                                user2
                            </td>
                            <td class="p-1 border">
                                test2@example.com
                            </td>
                            <td class="p-1 border">
                                0
                            </td>
                        </tr>
                    </tbody>
                </table>

                <b-form-file
                    ref="fileinput"
                    class="fileinput mt-1"
                    multiple
                    placeholder="Select file"
                    accept="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,
                        application/vnd.ms-excel"
                    @change="importRowsFromSpreadsheet"
                />
            </b-card>
        </b-modal>
    </div>
</template>

<script>
import ExcelJS from 'exceljs'

import userAPI from '@/api/user.js'

export default {
    data () {
        return {
            usersToInvite: [{
                full_name: '',
                username: '',
                email: '',
                is_teacher: false,
            }],
            errorLogs: null,
            requestInFlight: false,
        }
    },
    computed: {
        usersToInviteFiltered () {
            // Filter fully empty rows.
            return this.filterUsersToInvite()
        },
    },
    methods: {
        filterUsersToInvite () {
            const filteredUsers = []
            this.usersToInvite.forEach((user) => {
                const tempUser = {}
                tempUser.full_name = user.full_name.replace(/\s+/g, ' ').trim()
                tempUser.username = user.username.replace(/\s+/g, ' ').trim()
                tempUser.email = user.email.replace(/\s+/g, ' ').trim()

                if (tempUser.full_name || tempUser.username || tempUser.email) {
                    filteredUsers.push(tempUser)
                }
            })

            return filteredUsers
        },
        inviteUsers () {
            this.usersToInvite = this.filterUsersToInvite()
            this.requestInFlight = true
            userAPI.inviteUsers({
                users: this.usersToInvite,
            }, {
                customErrorToast: '',
                responseSuccessToast: true,
            })
                .then(() => {
                    this.requestInFlight = false
                    this.errorLogs = null
                    this.usersToInvite = [{
                        full_name: '',
                        username: '',
                        email: '',
                        is_teacher: false,
                    }]
                })
                .catch((error) => {
                    // Ensure old errors are cleared.
                    this.errorLogs = null
                    if (typeof error.response.data.description === 'object') {
                        this.$toasted.error('Some user details were invalid. No invites sent.')
                        this.errorLogs = error.response.data.description
                    } else {
                        this.$toasted.error(error.response.data.description)
                    }
                    this.requestInFlight = false
                })
        },
        addRow () {
            this.usersToInvite.push({
                full_name: '',
                username: '',
                email: '',
                is_teacher: false,
            })
        },
        importRowsFromSpreadsheet (event) {
            const workbook = new ExcelJS.Workbook()
            const fileReader = new FileReader()
            const importedUsersToInvite = []

            function asText (value) {
                if (!value) {
                    return null
                } else if (typeof value === 'object') {
                    return value.text.trim()
                }

                return value.trim()
            }

            if (!event.target.files.length > 0) {
                return
            }

            fileReader.readAsArrayBuffer(event.target.files[0]);
            fileReader.onload = () => {
                const buffer = fileReader.result;
                workbook.xlsx.load(buffer)
                    .then((wb) => {
                        wb.worksheets[0].eachRow((row) => {
                            const userRow = {
                                full_name: asText(row.values[1]),
                                username: asText(row.values[2]),
                                email: asText(row.values[3]),
                                is_teacher: row.values[4] === 1,
                            }

                            // Only import rows for which at least one column has a value.
                            if (Object.values(userRow).some(value => value)) {
                                importedUsersToInvite.push(userRow)
                            }
                        })
                        this.$toasted.success('Successfully imported user data from file.')
                        this.usersToInvite = importedUsersToInvite.concat(this.usersToInvite)
                        this.$refs['invite-user-file-upload-modal'].hide()
                    })
                    .catch(() => {
                        this.$toasted.error('Something went wrong while reading the file.')
                    })
            };
        },
        removeRow (user) {
            this.usersToInvite.splice(this.usersToInvite.indexOf(user), 1)
            if (this.usersToInvite.length === 0) {
                this.addRow()
            }
        },
    },
}
</script>
