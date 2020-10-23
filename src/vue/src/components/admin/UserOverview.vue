<template>
    <b-table-simple
        responsive
        striped
        sortBy="name"
        class="mt-2 mb-0 user-overview"
    >
        <b-thead>
            <b-tr class="d-flex">
                <b-th class="col-3">
                    Name
                </b-th>
                <b-th class="col-3">
                    Username
                </b-th>
                <b-th class="col-3">
                    Email
                </b-th>
                <b-th class="col-1">
                    Teacher
                </b-th>
                <b-th class="col-1">
                    Active
                </b-th>
                <b-th class="col-1"/>
            </b-tr>
        </b-thead>
        <b-tbody>
            <b-tr
                v-for="(user, i) in users"
                :key="i"
                class="d-flex"
            >
                <b-td class="col-3 truncate-content">
                    {{ user.full_name }}
                </b-td>
                <b-td class="col-3 truncate-content">
                    {{ user.username }}
                </b-td>
                <b-td class="col-3 truncate-content">
                    {{ user.email }}
                </b-td>
                <b-td class="col-1">
                    <icon
                        v-if="user.is_teacher"
                        name="check"
                        class="text-green"
                    />
                    <icon
                        v-else
                        name="times"
                        class="text-grey"
                    />
                </b-td>
                <b-td class="col-1">
                    <icon
                        v-if="user.is_active"
                        name="check"
                        class="text-green"
                    />
                    <icon
                        v-else
                        name="history"
                        class="text-yellow"
                    />
                </b-td>
                <b-td class="col-1">
                    <b-dropdown
                        lazy
                        noCaret
                        variant="link"
                    >
                        <icon
                            slot="button-content"
                            name="ellipsis-v"
                            class="move-icon"
                        />
                        <b-dropdown-item-button
                            v-if="user.id !== $store.getters['user/uID']"
                            @click="removeUser(user)"
                        >
                            Remove
                        </b-dropdown-item-button>
                        <b-dropdown-item-button
                            v-if="!user.is_teacher"
                            @click="makeTeacher(user)"
                        >
                            Make teacher
                        </b-dropdown-item-button>
                        <b-dropdown-item-button
                            v-if="user.is_teacher"
                            @click="removeTeacher(user)"
                        >
                            Remove teacher
                        </b-dropdown-item-button>
                    </b-dropdown>
                </b-td>
            </b-tr>
        </b-tbody>
    </b-table-simple>
</template>

<script>
import adminAPI from '@/api/admin.js'

export default {
    data () {
        return {
            users: [],
        }
    },
    created () {
        this.getAllUsers()
    },
    methods: {
        getAllUsers () {
            adminAPI.getAllUsers()
                .then((users) => { this.users = users })
        },
        removeUser (user) {
            if (window.confirm(`Are you sure you want to remove ${user.full_name}? All of their work will be deleted.`
                + 'This includes courses which they are the author of. This cannot be undone!')) {
                adminAPI.removeUser(user.id)
                    .then(() => { this.$toasted.success('Successfully removed user.') })
                    .finally(() => {
                        this.getAllUsers()
                    })
            }
        },
        makeTeacher (user) {
            this.$toasted.info(`TODO: Make teacher ${user.full_name}`)
        },
        removeTeacher (user) {
            this.$toasted.info(`TODO: Remove teacher ${user.full_name}`)
        },
    },
}
</script>

<style lang="sass">
.user-overview
    td.truncate-content
        white-space: nowrap
        overflow: hidden
        text-overflow: ellipsis
</style>
