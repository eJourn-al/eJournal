<template>
    <div>
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
                @click="showModal('createAssignmentRef')"
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
        <div v-if="linkableAssignments.some(linkable => linkable.assignments.length > 0)">
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
        <link-assignment-modal
            ref="linkAssignmentRef"
            :lti="lti"
            :page="page"
            :linkableAssignments="linkableAssignments"
            @handleAction="handleLinked"
        />
        <assignment-import-modal
            modalID="lti-assignment-import-modal"
            :cID="page.cID"
            :lti="lti"
        />
        <create-assignment-modal
            ref="createAssignmentRef"
            :lti="lti"
            :page="page"
            @handleAction="handleCreated"
        />
    </div>
</template>

<script>
import LinkAssignmentModal from '@/components/lti/LinkAssignmentModal.vue'

import assignmentImportModal from '@/components/assignment/AssignmentImportModal.vue'
import createAssignmentModal from '@/components/assignment/CreateAssignmentModal.vue'

export default {
    name: 'LtiCreateLinkAssignment',
    components: {
        createAssignmentModal,
        assignmentImportModal,
        LinkAssignmentModal,
    },
    props: ['lti', 'page', 'linkableAssignments'],
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
        handleCreated (aID) {
            this.hideModal('createAssignmentRef')
            this.signal(['assignmentCreated', aID])
        },
        handleLinked (aID) {
            this.hideModal('linkAssignmentRef')
            this.signal(['assignmentIntegrated', aID])
        },
    },
}
</script>
