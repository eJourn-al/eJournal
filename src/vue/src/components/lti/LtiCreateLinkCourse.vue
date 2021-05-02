<template>
    <div>
        <load-wrapper
            :loading="loadingCourses"
            :timeBeforeShow="0"
        >
            <h2 class="theme-h2 mb-2">
                Configuring a Course
            </h2>
            <p>
                You came here from a learning environment through an unconfigured
                course. Do you want to create a new course on eJournal,
                or link it to an existing one?
            </p>
            <hr/>
            <div class="clearfix">
                <p class="mb-1">
                    If you have not yet preconfigured this course on eJournal, click the button below
                    to create a new course. This will be linked to your learning environment, allowing for automatic
                    grade passback.
                </p>
                <b-button
                    class="green-button float-right"
                    @click="createCourse"
                >
                    <icon name="plus-square"/>
                    Create new course
                </b-button>
            </div>
            <hr/>
            <div class="clearfix">
                <p class="mb-1">
                    If you have already set up a course on eJournal, you can link it to the course in
                    your learning environment by clicking the button below.
                </p>
                <b-button
                    class="orange-button float-right"
                    @click="showModal('linkCourseRef')"
                >
                    <icon name="link"/>
                    Link to existing course
                </b-button>
            </div>
        </load-wrapper>

        <link-course-modal
            ref="linkCourseRef"
            :courses="courses"
            @courseLinked="(course) => $emit('courseLinked', course)"
        />
    </div>
</template>

<script>
import courseAPI from '@/api/course.js'
import linkCourseModal from '@/components/lti/LinkCourseModal.vue'
import loadWrapper from '@/components/loading/LoadWrapper.vue'

export default {
    name: 'LtiCreateLinkCourse',
    components: {
        linkCourseModal,
        loadWrapper,
    },
    data () {
        return {
            courses: [],
            loadingCourses: true,
        }
    },
    created () {
        courseAPI.getLinkable().then((courses) => {
            if (courses.length) {
                this.courses = courses
                this.loadingCourses = false
            } else {
                this.createCourse()
            }
        })
    },
    methods: {
        createCourse () {
            courseAPI.create({ launch_id: this.$route.query.launch_id })
                .then((course) => { this.$emit('courseCreated', course) })
        },
        showModal (ref) {
            this.$refs[ref].show()
        },
    },
}
</script>
