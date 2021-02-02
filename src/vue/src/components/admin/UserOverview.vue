<template>
    <div>
        <b-input
            v-model="filter"
            class="theme-input full-width mb-2"
            placeholder="Search by name, username or email"
            debounce="500"
        />

        <!-- eslint-disable vue/attribute-hyphenation -->
        <b-pagination
            v-model="currentPage"
            :total-rows="rows"
            :per-page="perPage"
            align="center"
            aria-controls="user-table"
            first-number
            last-number
        />
        <b-table
            id="user-table"
            ref="table"
            :items="provider"
            :fields="fields"
            :per-page="perPage"
            :current-page="currentPage"
            :filter="filter"
            :sortBy="sortBy"
            responsive
            striped
            class="mt-2 mb-0 user-overview"
            primary-key="id"
        >
            <!-- eslint-enable vue/attribute-hyphenation -->

            <template #table-busy>
                <load-spinner class="mt-2"/>
            </template>

            <template #cell(is_teacher)="data">
                <icon
                    :name="data.value ? 'check' : 'times'"
                    :class="data.value ? 'text-green' : 'text-grey'"
                />
            </template>

            <template #cell(is_active)="data">
                <icon
                    :name="data.value ? 'check' : 'history'"
                    :class="data.value ? 'text-green' : 'text-yellow'"
                />
            </template>

            <template #cell(action)="data">
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
                        v-if="data.item.id !== $store.getters['user/uID']"
                        @click="removeUser(data.item)"
                    >
                        Remove
                    </b-dropdown-item-button>
                    <b-dropdown-item-button
                        v-if="!data.item.is_teacher"
                        @click="makeTeacher(data.item)"
                    >
                        Make teacher
                    </b-dropdown-item-button>
                    <b-dropdown-item-button
                        v-else
                        @click="removeTeacher(data.item)"
                    >
                        Remove teacher
                    </b-dropdown-item-button>
                </b-dropdown>
            </template>
        </b-table>
    </div>
</template>

<script>
import loadSpinner from '@/components/loading/LoadSpinner.vue'
import userAPI from '@/api/user.js'

export default {
    components: {
        loadSpinner,
    },
    data () {
        return {
            currentPage: 1,
            rows: 0,
            perPage: 100,
            filter: '',
            sortBy: 'full_name',
            fields: [
                {
                    key: 'full_name',
                    label: 'Name',
                    sortable: true,
                },
                {
                    key: 'username',
                    sortable: true,
                },
                {
                    key: 'email',
                    sortable: true,
                },
                {
                    key: 'is_teacher',
                    label: 'Teacher',
                    sortable: true,
                },
                {
                    key: 'is_active',
                    label: 'Active',
                    sortable: true,
                },
                {
                    key: 'action',
                    label: '',
                },
            ],
        }
    },
    methods: {
        removeUser (user) {
            if (window.confirm(`Are you sure you want to remove ${user.full_name}? All of their work will be deleted.`
                + 'This cannot be undone!')) {
                userAPI.delete(user.id, { customSuccessToast: `Successfully removed ${user.full_name}.` })
                    .finally(() => { this.$refs.table.refresh() })
            }
        },
        makeTeacher (user) {
            userAPI.update(
                user.id,
                { is_teacher: true },
                { customSuccessToast: `Successfully made ${user.full_name} teacher.` },
            )
                .finally(() => { this.$refs.table.refresh() })
        },
        removeTeacher (user) {
            userAPI.update(
                user.id,
                { is_teacher: false },
                { customSuccessToast: `Successfully removed ${user.full_name} as a teacher.` },
            )
                .finally(() => { this.$refs.table.refresh() })
        },
        provider (context, callback) {
            userAPI.list({
                page: this.currentPage,
                page_size: context.perPage,
                filter: context.filter,
                order_by: `${context.sortDesc ? '-' : ''}${context.sortBy}`,
            })
                .then((data) => {
                    this.rows = data.count
                    callback(data.results)
                })
                .catch(() => {
                    callback([])
                })

            /* Must return null or undefined to signal b-table that callback is being used */
            return null
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

#user-table[aria-busy='true']
    opacity: 1.0
</style>
