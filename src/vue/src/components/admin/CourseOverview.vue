<template>
    <b-table-simple
        responsive
        striped
        sortBy="name"
        class="mt-2 mb-0 course-overview"
    >
        <b-thead>
            <b-tr class="d-flex">
                <b-th class="col-4">
                    Name
                </b-th>
                <b-th class="col-2">
                    Id
                </b-th>
                <b-th class="col-2">
                    Start
                </b-th>
                <b-th class="col-2">
                    End
                </b-th>
                <b-th class="col-1">
                    LTI
                </b-th>
                <b-th class="col-1"/>
            </b-tr>
        </b-thead>
        <b-tbody>
            <b-tr
                v-for="(course, i) in courses"
                :key="i"
                class="d-flex"
            >
                <b-td
                    :title="course.name"
                    class="col-4 truncate-content"
                >
                    {{ course.name }}
                </b-td>
                <b-td
                    :title="course.id"
                    class="col-2 truncate-content"
                >
                    {{ course.id }}
                </b-td>
                <b-td
                    class="col-2 truncate-content"
                >
                    {{ $root.beautifyDate(course.startdate, true, false) }}
                </b-td>
                <b-td
                    class="col-2 truncate-content"
                >
                    {{ $root.beautifyDate(course.enddate, true, false) }}
                </b-td>
                <b-td
                    class="col-1"
                >
                    <icon
                        v-if="course.lti_linked"
                        name="link"
                        class="text-blue"
                    />
                    <icon
                        v-else
                        name="unlink"
                        class="text-grey"
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
                        <router-link
                            :to="{ name: 'Course', params: { cID: course.id } }"
                            target="_blank"
                        >
                            <b-dropdown-item-button>
                                Visit
                            </b-dropdown-item-button>
                        </router-link>
                    </b-dropdown>
                </b-td>
            </b-tr>
        </b-tbody>
    </b-table-simple>
</template>

<script>
import courseAPI from '@/api/course.js'

export default {
    data () {
        return {
            courses: [],
            loadingCourses: true,
        }
    },
    created () {
        this.getAllCourses()
    },
    methods: {
        getAllCourses () {
            courseAPI.list({ get_all: true })
                .then((courses) => { this.courses = courses })
        },
        actionFunction () {
            this.$toasted.info('Not implemented action')
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
