<template>
    <content-columns>
        <bread-crumb slot="main-content-column"/>

        <load-wrapper
            slot="main-content-column"
            :loading="loadingCourses"
        >
            <b-table-simple
                v-if="courses.length > 0"
                responsive
                striped
                hover
                class="mt-2 mb-0 bordered-content no-top-table-border"
            >
                <b-thead>
                    <b-tr>
                        <b-th>
                            Name
                        </b-th>
                        <b-th>
                            Year
                        </b-th>
                    </b-tr>
                </b-thead>
                <b-tbody>
                    <b-tr
                        v-for="(course, i) in courses"
                        :key="i"
                        class="cursor-pointer"
                        @click="$router.push({ name: 'Course', params: { cID: course.id, courseName: course.name } })"
                    >
                        <b-td :title="course.name">
                            <b-link
                                :to="{ name: 'Course', params: { cID: course.id, courseName: course.name } }"
                                @click.prevent.stop
                            >
                                {{ course.name }}
                            </b-link>
                        </b-td>
                        <b-td>
                            <b-badge
                                v-if="course.startdate || course.enddate"
                                pill
                                class="background-blue"
                            >
                                {{ courseDateDisplay(course) }}
                            </b-badge>
                        </b-td>
                    </b-tr>
                </b-tbody>
            </b-table-simple>
            <not-found
                v-else
                subject="courses"
                explanation="You currently do not participate in any courses."
            >
                <b-button
                    v-if="$hasPermission('can_add_course')"
                    class="green-button d-block ml-auto mr-auto mt-2"
                    @click="showModal('createCourseRef')"
                >
                    <icon name="plus"/>
                    Create new course
                </b-button>
            </not-found>
        </load-wrapper>

        <deadline-deck
            slot="right-content-column"
            class="mb-3"
        />
        <b-card
            v-if="courses.length > 0 && $hasPermission('can_add_course')"
            slot="right-content-column"
        >
            <h3
                slot="header"
                class="theme-h3"
            >
                Actions
            </h3>
            <b-button
                v-if="$hasPermission('can_add_course')"
                variant="link"
                class="green-button"
                @click="showModal('createCourseRef')"
            >
                <icon name="plus"/>
                Create new course
            </b-button>
        </b-card>

        <create-course-modal
            slot="main-content-column"
            ref="createCourseRef"
            @handleAction="handleConfirm('createCourseRef')"
        />
    </content-columns>
</template>

<script>
import breadCrumb from '@/components/assets/BreadCrumb.vue'
import contentColumns from '@/components/columns/ContentColumns.vue'
import createCourseModal from '@/components/course/CreateCourseModal.vue'
import deadlineDeck from '@/components/assets/DeadlineDeck.vue'
import loadWrapper from '@/components/loading/LoadWrapper.vue'

import courseAPI from '@/api/course.js'

export default {
    name: 'Home',
    components: {
        contentColumns,
        breadCrumb,
        loadWrapper,
        createCourseModal,
        deadlineDeck,
    },
    data () {
        return {
            courses: [],
            loadingCourses: true,
        }
    },
    created () {
        this.loadCourses()
    },
    methods: {
        loadCourses () {
            courseAPI.list()
                .then((courses) => {
                    this.courses = courses
                    this.loadingCourses = false
                })
        },
        showModal (ref) {
            this.$refs[ref].show()
        },
        handleConfirm (ref) {
            if (ref === 'createCourseRef') {
                this.loadCourses()
            }

            this.hideModal(ref)
        },
        hideModal (ref) {
            this.$refs[ref].hide()
        },
        courseDateDisplay (course) {
            let display = ''

            if (course.startdate) { display += course.startdate.substring(0, 4) }
            if (course.startdate && course.enddate) { display += ' - ' }
            if (course.enddate) { display += course.enddate.substring(0, 4) }

            return display
        },
    },
}
</script>
