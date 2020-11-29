<template>
    <content-columns>
        <bread-crumb slot="main-content-column"/>

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
                            :text="c.name"
                            :class="$root.getBorderClass(c.id)"
                        >
                            <b-badge
                                pill
                                class="background-blue"
                            >
                                {{ c.startdate ? (c.startdate.substring(0, 4) +
                                    (c.enddate ? ` - ${c.enddate.substring(0, 4)}` : '')) : '' }}
                            </b-badge>
                        </main-card>
                    </b-link>
                </div>
            </div>
            <main-card
                v-else
                text="No courses found"
                class="no-hover"
            >
                You currently do not participate in any courses.
            </main-card>
            <b-button
                v-if="$hasPermission('can_add_course')"
                class="green-button"
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
    },
}
</script>
