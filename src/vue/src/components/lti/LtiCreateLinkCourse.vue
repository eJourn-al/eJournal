<template>
    <div v-if="courses">
        <h2 class="theme-h2 multi-form">
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
                @click="showModal('createCourseRef')"
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

        <b-modal
            ref="createCourseRef"
            title="New Course"
            size="lg"
            hideFooter
            noEnforceFocus
        >
            <create-course
                :lti="lti"
                @handleAction="handleCreation"
            />
        </b-modal>

        <b-modal
            ref="linkCourseRef"
            title="Link Course"
            size="lg"
            hideFooter
            noEnforceFocus
        >
            <link-course
                :lti="lti"
                :courses="courses"
                @handleAction="handleLinked"
            />
        </b-modal>
    </div>
</template>

<script>
import createCourse from '@/components/course/CreateCourse.vue'
import linkCourse from '@/components/lti/LinkCourse.vue'

export default {
    name: 'LtiCreateLinkCourse',
    components: {
        createCourse,
        linkCourse,
    },
    props: ['lti', 'courses'],
    methods: {
        signal (msg) {
            this.$emit('handleAction', msg)
        },
        showModal (ref) {
            this.$refs[ref].show()
        },
        hideModal (ref) {
            this.$refs[ref].hide()
        },
        handleCreation (cID) {
            this.hideModal('createCourseRef')
            this.signal(['courseCreated', cID])
        },
        handleLinked (cID) {
            this.hideModal('linkCourseRef')
            this.signal(['courseLinked', cID])
        },
    },
}
</script>
