<template>
    <load-wrapper :loading="loadingUsers">
        <b-input
            v-model="searchValue"
            class="theme-input full-width mb-2"
            placeholder="Search by name, username or email"
        />
        <b-table-simple
            responsive
            striped
            sortBy="name"
            class="mt-2 mb-0 user-overview"
        >
            <b-thead>
                <b-tr class="d-flex">
                    <b-th class="col-3 truncate-content">
                        Name
                    </b-th>
                    <b-th class="col-3 truncate-content">
                        Username
                    </b-th>
                    <b-th class="col-3 truncate-content">
                        Email
                    </b-th>
                    <b-th class="col-1 truncate-content">
                        Teacher
                    </b-th>
                    <b-th class="col-1 truncate-content">
                        Active
                    </b-th>
                    <b-th class="col-1"/>
                </b-tr>
            </b-thead>
            <b-tbody>
                <b-tr
                    v-for="(user, i) in filteredUsers"
                    :key="i"
                    class="d-flex"
                >
                    <b-td
                        :title="user.full_name"
                        class="col-3 truncate-content"
                    >
                        {{ user.full_name }}
                    </b-td>
                    <b-td
                        :title="user.username"
                        class="col-3 truncate-content"
                    >
                        {{ user.username }}
                    </b-td>
                    <b-td
                        :title="user.email"
                        class="col-3 truncate-content"
                    >
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
                                v-else
                                @click="removeTeacher(user)"
                            >
                                Remove teacher
                            </b-dropdown-item-button>
                        </b-dropdown>
                    </b-td>
                </b-tr>
            </b-tbody>
        </b-table-simple>
    </load-wrapper>
</template>

<script>
import userAPI from '@/api/user.js'

import loadWrapper from '@/components/loading/LoadWrapper.vue'

export default {
    components: {
        loadWrapper,
    },
    data () {
        return {
            users: [],
            searchValue: '',
            loadingUsers: true,
        }
    },
    computed: {
        filteredUsers () {
            return this.users.filter(user => user.full_name.toLowerCase().includes(this.searchValue.toLowerCase())
                || user.username.toLowerCase().includes(this.searchValue.toLowerCase())
                || (user.email && user.email.toLowerCase().includes(this.searchValue.toLowerCase())))
        },
    },
    created () {
        this.getAllUsers()
    },
    methods: {
        getAllUsers () {
            userAPI.getAllUsers()
                .then((users) => { this.users = users })
                .finally(() => { this.loadingUsers = false })
        },
        removeUser (user) {
            if (window.confirm(`Are you sure you want to remove ${user.full_name}? All of their work will be deleted.`
                + 'This cannot be undone!')) {
                userAPI.delete(user.id)
                    .then(() => { this.$toasted.success('Successfully removed user.') })
                    .finally(() => {
                        this.getAllUsers()
                    })
            }
        },
        makeTeacher (user) {
            userAPI.update(user.id, { is_teacher: true })
                .then(() => { this.$toasted.success(`Successfully made ${user.full_name} teacher.`) })
                .finally(() => {
                    this.getAllUsers()
                })
        },
        removeTeacher (user) {
            userAPI.update(user.id, { is_teacher: false })
                .then(() => { this.$toasted.success(`Successfully removed ${user.full_name} as a teacher.`) })
                .finally(() => {
                    this.getAllUsers()
                })
        },
    },
}
</script>

<style lang="sass">
.user-overview
    td.truncate-content, th.truncate-content
        white-space: nowrap
        overflow: hidden
        text-overflow: ellipsis
</style>
