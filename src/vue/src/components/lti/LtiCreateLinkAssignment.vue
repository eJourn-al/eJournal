
<template>
    <div>
        <load-wrapper
            :loading="loadingAssignments"
            :timeBeforeShow="0"
        >
            <h2 class="theme-h2 mb-2">
                Configuring an assignment
            </h2>
            <span class="d-block mb-2">
                You came here from a learning management system through an unconfigured
                assignment. Select one of the options below to perform a one-time configuration.
            </span>
            <hr/>
            <div class="clearfix">
                <p class="mb-1">
                    If you have not yet preconfigured this assignment on eJournal, click the button below
                    to create a new assignment.
                </p>

                <b-button
                    class="green-button float-right"
                    @click="createAssignment"
                >
                    <icon name="plus-square"/>
                    Create new assignment
                </b-button>
            </div>
            <hr/>
            <div class="clearfix">
                <p class="mb-1">
                    If you want to create a new assignment that is identical to an assignment that you have
                    already configured, click the button below to import it. Existing journals are not imported
                    and will remain accessible only from the original assignment.
                </p>
                <b-button
                    v-b-modal="'lti-assignment-import-modal'"
                    class="orange-button float-right"
                >
                    <icon name="file-import"/>
                    Import existing assignment
                </b-button>
            </div>
            <div v-if="assignments && assignments.some(linkable => linkable.assignments.length > 0)">
                <hr/>
                <p class="mb-1">
                    If you have already configured an assignment on eJournal, you can link it to the assignment in
                    your learning management system by clicking the button below. This allows students to continue
                    working on their existing journals related to this assignment.
                </p>
                <b-button
                    class="orange-button float-right"
                    @click="showModal('linkAssignmentRef')"
                >
                    <icon name="link"/>
                    Link to existing assignment
                </b-button>
            </div>
        </load-wrapper>

        <link-assignment-modal
            ref="linkAssignmentRef"
            :linkableAssignments="linkableAssignments"
            @assignmentLinked="(assignment) => $emit('assignmentLinked', assignment)"
        />
        <assignment-import-modal
            modalID="lti-assignment-import-modal"
            @assignmentImported="(assignment) => $emit('assignmentImported', assignment)"
        />
    </div>
</template>

<script>
import assignmentAPI from '@/api/assignment.js'
import assignmentImportModal from '@/components/assignment/AssignmentImportModal.vue'
import linkAssignmentModal from '@/components/lti/LinkAssignmentModal.vue'
import loadWrapper from '@/components/loading/LoadWrapper.vue'

export default {
    name: 'LtiCreateLinkAssignment',
    components: {
        linkAssignmentModal,
        assignmentImportModal,
        loadWrapper,
    },
    data () {
        return {
            assignments: [],
            linkableAssignments: [],
            loadingAssignments: true,
        }
    },
    created () {
        assignmentAPI.getImportable({ launch_id: this.$route.query.launch_id }).then((assignments) => {
            if (assignments.length) {
                this.assignments = assignments
                this.linkableAssignments = assignments.slice()
                for (let i = 0; i < this.linkableAssignments.length; i++) {
                    this.linkableAssignments[i].assignments = this.linkableAssignments[i].assignments.filter(
                        (assignment) => !assignment.active_lti_course
                        || assignment.active_lti_course.course_id !== (this.$route.query.course_id || this.page.cID))
                }
                this.loadingAssignments = false
            } else {
                this.createAssignment()
            }
        })
    },
    methods: {
        createAssignment () {
            assignmentAPI.create({ launch_id: this.$route.query.launch_id }, { responseSuccessToast: true })
                .then((assignment) => { this.$emit('assignmentCreated', assignment) })
        },
        showModal (ref) {
            this.$refs[ref].show()
        },
    },
}
</script>
