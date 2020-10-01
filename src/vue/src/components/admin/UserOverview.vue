<template>
    <b-table-simple
        responsive
        striped
        noSortReset
        sortBy="name"
        class="mt-2 mb-0"
    >
        <b-thead>
            <b-tr>
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
                    Status
                </b-th>
                <b-th/>
            </b-tr>
        </b-thead>
        <b-tbody>
            <b-tr
                v-for="(user, i) in users"
                :key="i"
            >
                <b-td class="align-middle">
                    {{ user.full_name }}
                </b-td>
                <b-td class="align-middle">
                    {{ user.username }}
                </b-td>
                <b-td class="align-middle">
                    {{ user.email }}
                </b-td>
                <b-td class="align-middle">
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
                <b-td class="align-middle">
                    <b-dropdown
                        lazy
                        noCaret
                        variant="link"
                    >
                        <icon
                            slot="button-content"
                            name="ellipsis-v"
                            class="trash-icon"
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
