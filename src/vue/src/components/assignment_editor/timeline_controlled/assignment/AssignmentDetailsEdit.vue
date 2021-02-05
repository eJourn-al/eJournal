<template>
    <b-card
        :class="$root.getBorderClass($route.params.cID)"
        class="no-hover"
    >
        <b-row
            no-gutters
            class="multi-form"
        >
            <span class="theme-h2">Assignment details</span>

            <b-button
                class="red-button ml-auto"
                @click="clearAssignmentDetailsDraft(); selectAssignmentDetails({ originalAssignment })"
            >
                <icon name="ban"/>
                Cancel
            </b-button>
        </b-row>

        <assignment-details
            ref="assignmentDetails"
            :assignmentDetails="assignmentDetailsDraft"
            :presetNodes="assignmentPresetNodes"
        />

        <hr/>

        <b-button
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

            this.updateAssignment({ id: this.assignmentDetailsDraft.id, data: this.assignmentDetailsDraft })
                .then(() => {
                    this.clearAssignmentDetailsDraft()
                    this.selectAssignmentDetails({ originalAssignment: this.originalAssignment })
                    this.setModeToRead()
                })
        },
    },
}
</script>
