<template>
    <b-card>
        <template #header>
            <b-button
                class="red-button float-right"
                @click="clearAssignmentDetailsDraft(); selectAssignmentDetails({ originalAssignment })"
            >
                <icon name="ban"/>
                Cancel
            </b-button>
            <h2 class="theme-h2">
                Assignment details
            </h2>
        </template>

        <assignment-details
            v-if="assignmentDetailsDraft.all_groups && assignmentDetailsDraft.assigned_groups"
            ref="assignmentDetails"
            :assignmentDetails="assignmentDetailsDraft"
            :presetNodes="assignmentPresetNodes"
        />

        <b-button
            slot="footer"
            class="float-right green-button"
            @click.stop="save()"
        >
            <icon name="save"/>
            Save
        </b-button>
    </b-card>
</template>

<script>
import AssignmentDetails from '@/components/assignment/AssignmentDetails.vue'

import { mapActions, mapGetters, mapMutations } from 'vuex'

import groupAPI from '@/api/group.js'

export default {
    name: 'AssignmentDetailsEdit',
    components: {
        AssignmentDetails,
    },
    computed: {
        ...mapGetters({
            originalAssignment: 'assignment/assignment',
            assignmentDetailsDraft: 'assignmentEditor/assignmentDetailsDraft',
            assignmentPresetNodes: 'presetNode/assignmentPresetNodes',
        }),
    },
    created () {
        /*
         * Insert assigned groups data to the assignment.
         * These fields can only be set on the assignment editor page, and are therefore not serialized as a default
         * part of the assignment.
         *
         * However, they are updated as part of the assignment API, since another save button (for the assigned groups)
         * is not appropriate.
         */
        groupAPI.getAllFromCourse(this.$route.params.cID).then((courseGroups) => {
            this.$set(this.assignmentDetailsDraft, 'all_groups', courseGroups)
            this.$set(this.originalAssignment, 'all_groups', courseGroups)
        })
        groupAPI.getAssignedGroups(this.$route.params.cID, this.$route.params.aID).then((assignedGroups) => {
            this.$set(this.assignmentDetailsDraft, 'assigned_groups', assignedGroups)
            this.$set(this.originalAssignment, 'assigned_groups', assignedGroups)
        })
    },
    methods: {
        ...mapActions({
            updateAssignment: 'assignment/update',
        }),
        ...mapMutations({
            clearAssignmentDetailsDraft: 'assignmentEditor/CLEAR_ASSIGNMENT_DETAILS_DRAFT',
            selectAssignmentDetails: 'assignmentEditor/SELECT_ASSIGNMENT_DETAILS',
            setModeToRead: 'assignmentEditor/SET_ACTIVE_COMPONENT_MODE_TO_READ',
        }),
        save () {
            if (!this.$refs.assignmentDetails.validateData()
                || !this.$refs.assignmentDetails.$refs.assignmentDetailsDates.validateData()) {
                return
            }

            this.updateAssignment({
                id: this.assignmentDetailsDraft.id,
                data: this.assignmentDetailsDraft,
                cID: this.$route.params.cID,
            })
                .then(() => {
                    this.clearAssignmentDetailsDraft()
                    this.selectAssignmentDetails({ originalAssignment: this.originalAssignment })
                    this.setModeToRead()
                })
        },
    },
}
</script>
