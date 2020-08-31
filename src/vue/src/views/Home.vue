<template>
    <content-columns>
        <bread-crumb
            slot="main-content-column"
            :currentPage="'Courses'"
            @edit-click="handleEdit()"
        />

        <load-wrapper
            slot="main-content-column"
            :loading="loadingCourses"
        >
            <div v-if="courses.length > 0">
                <div
                    v-for="c in courses"
                    :key="c.id"
                >
                    <b-link :to="{ name: 'Course', params: { cID: c.id, courseName: c.name } }">
                        <main-card
                            :line1="c.name"
                            :line2="c.startdate ? (c.startdate.substring(0, 4) +
                                (c.enddate ? ` - ${c.enddate.substring(0, 4)}` : '')) : ''"
                            :color="$root.getBorderClass(c.id)"
                        />
                    </b-link>
                </div>
            </div>
            <main-card
                v-else
                line1="No courses found"
                line2="You currently do not participate in any courses."
                class="no-hover border-dark-grey"
            />
            <b-button
                v-if="$hasPermission('can_add_course')"
                class="add-button"
                @click="showModal('createCourseRef')"
            >
                <icon name="plus"/>
                Create new course
            </b-button>
        </load-wrapper>

        <deadline-deck slot="right-content-column"/>

        <b-modal
            slot="main-content-column"
            ref="editCourseRef"
            title="Global Changes"
            size="lg"
            hideFooter
            noEnforceFocus
        >
            <edit-home @handleAction="handleConfirm('editCourseRef')"/>
        </b-modal>

        <b-modal
            slot="main-content-column"
            ref="createCourseRef"
            title="New Course"
            size="lg"
            hideFooter
            noEnforceFocus
        >
            <create-course @handleAction="handleConfirm('createCourseRef')"/>
        </b-modal>
    </content-columns>
</template>

<script>
import contentColumns from '@/components/columns/ContentColumns.vue'
import breadCrumb from '@/components/assets/BreadCrumb.vue'
import loadWrapper from '@/components/loading/LoadWrapper.vue'
import mainCard from '@/components/assets/MainCard.vue'
import createCourse from '@/components/course/CreateCourse.vue'
import editHome from '@/components/home/EditHome.vue'
import deadlineDeck from '@/components/assets/DeadlineDeck.vue'

import courseAPI from '@/api/course.js'

export default {
    name: 'Home',
    components: {
        contentColumns,
        breadCrumb,
        loadWrapper,
        mainCard,
        createCourse,
        editHome,
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
            courseAPI.getUserEnrolled()
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
        handleEdit () {
            // TODO: Open EditHome
        },
        hideModal (ref) {
            this.$refs[ref].hide()
        },
    },
}
</script>
