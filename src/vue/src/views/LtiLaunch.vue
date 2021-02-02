<template>
    <content-single-column>
        <h1
            v-if="currentPage"
            class="theme-h1 mb-2"
        >
            <span>{{ currentPage }}</span>
        </h1>
        <b-card
            v-if="currentPage"
            class="no-hover"
        >
            <lti-create-link-course
                v-if="launchState === states.noCourse"
                @courseCreated="handleCourse"
                @courseLinked="handleCourse"
            />
            <lti-create-link-assignment
                v-else-if="launchState === states.noAssignment"
                @assignmentCreated="handleAssignment"
                @assignmentLinked="handleAssignment"
                @assignmentImported="handleAssignment"
            />
        </b-card>
        <load-spinner
            v-else
            class="mt-5"
        />
    </content-single-column>
</template>

<script>
import contentSingleColumn from '@/components/columns/ContentSingleColumn.vue'
import loadSpinner from '@/components/loading/LoadSpinner.vue'
import ltiCreateLinkAssignment from '@/components/lti/LtiCreateLinkAssignment.vue'
import ltiCreateLinkCourse from '@/components/lti/LtiCreateLinkCourse.vue'

export default {
    name: 'LtiLaunch',
    components: {
        contentSingleColumn,
        loadSpinner,
        ltiCreateLinkCourse,
        ltiCreateLinkAssignment,
    },
    data () {
        return {
            currentPage: '',
            launchState: this.$route.query.launch_state,
            params: {
                cID: this.$route.query.course_id,
                aID: this.$route.query.assignment_id,
                jID: this.$route.query.journal_id,
            },
            /* Possible states for the control flow. */
            states: {
                /* Extern variables for checking the state of the lti launch. */
                notSetup: '-1',

                noCourse: '1',
                noAssignment: '2',
                finishTeacher: '3',
                finishStudent: '4',
            },
        }
    },
    mounted () {
        if (this.launchState === this.states.lacking_permissions_to_setup_assignment
            || this.launchState === this.states.lacking_permissions_to_setup_course) {
            this.$router.push({
                name: 'NotSetup',
                query: this.$route.query,
            })
            return
        }
        if (this.launchState === this.states.noCourse) {
            this.initSetupCourse()
        } else if (this.launchState === this.states.noAssignment) {
            this.initSetupAssignment()
        } else if (this.launchState === this.states.finishTeacher) {
            /* If a journal id is set, it is in the gradebook. */
            if (this.$route.query.journal_id) {
                this.goto('Journal')
            } else {
                this.goto('Assignment')
            }
        } else if (this.launchState === this.states.finishStudent) {
            /* If journal id is not set, it is a group assignment, and it should go to JoinJournal. */
            if (this.$route.query.journal_id) {
                this.goto('Journal')
            } else {
                this.goto('JoinJournal')
            }
        }
    },
    methods: {
        initSetupCourse () {
            this.currentPage = 'Setup the course'
        },
        initSetupAssignment () {
            this.currentPage = 'Setup the assignment'
        },
        handleCourse (course) {
            this.params.cID = course.id
            this.launchState = this.states.noAssignment
        },
        handleAssignment (assignment) {
            this.params.aID = assignment.id
            this.$store.dispatch('user/populateStore').then(this.goto('FormatEdit'))
        },
        goto (route) {
            this.$router.push({
                name: route,
                params: this.params,
            })
        },
    },
}
</script>
