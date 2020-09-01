<template>
    <div>
        <load-wrapper
            :loading="loadingCourses"
            :timeBeforeShow="0"
        >
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
                    class="add-button float-right"
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
                    class="change-button float-right"
                    @click="showModal('linkCourseRef')"
                >
                    <icon name="link"/>
                    Link to existing course
                </b-button>
            </div>
        </load-wrapper>
        <b-modal
            ref="linkCourseRef"
            title="Link Course"
            size="lg"
            hideFooter
            noEnforceFocus
        >
            <link-course
                :courses="courses"
                @courseLinked="(course) => $emit('courseLinked', course)"
            />
        </b-modal>
    </div>
</template>

<script>
import linkCourse from '@/components/lti/LinkCourse.vue'
import courseAPI from '@/api/course.js'
import loadWrapper from '@/components/loading/LoadWrapper.vue'

export default {
    name: 'LtiCreateLinkCourse',
    components: {
        linkCourse,
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
