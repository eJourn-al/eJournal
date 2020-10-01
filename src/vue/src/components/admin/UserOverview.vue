<template>
    <b-table-simple
        responsive
        striped
        noSortReset
        sortBy="name"
        class="mt-2 mb-0 user-overview"
    >
        <b-thead>
            <b-tr class="d-flex">
                <b-th class="col-4">
                    Name
                </b-th>
                <b-th class="col-3">
                    Username
                </b-th>
                <b-th class="col-3">
                    Email
                </b-th>
                <b-th class="col-1">
                    Status
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
                <b-td class="align-middle col-4">
                    {{ user.full_name }}
                </b-td>
                <b-td class="align-middle col-3 username-column">
                    {{ user.username }}
                </b-td>
                <b-td class="align-middle col-3">
                    {{ user.email }}
                </b-td>
                <b-td class="align-middle col-1">
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
                <b-td class="align-middle col-1">
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
                        <b-dropdown-item-button @click="removeUser(user)">
                            Remove
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
        adminAPI.getAllUsers()
            .then((users) => { this.users = users })
    },
    methods: {
        removeUser (user) {
            this.$toasted.info(`TODO: Remove user ${user.full_name}`)
        },
    },
}
</script>

<style lang="sass">
.user-overview
    .username-column
        white-space: nowrap
        overflow: hidden
        text-overflow: ellipsis
</style>
