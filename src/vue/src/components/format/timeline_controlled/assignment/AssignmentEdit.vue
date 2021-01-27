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
                @click="setModeToRead()"
            >
                <icon name="ban"/>
                Cancel
            </b-button>
        </b-row>

        <assignment-details
            :assignmentDetails="assignment"
            :presetNodes="assignmentPresetNodes"
        />

        <hr/>

        <b-button
            class="float-right green-button"
            @click.stop="updateAssignment(assignment).then(() => { setModeToEdit() })"
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
    name: 'FormatSelectedTimelineItemsSwitch',
    components: {
        AssignmentDetails,
    },
    computed: {
        ...mapGetters({
            assignment: 'assignment/assignment',
            assignmentPresetNodes: 'presetNode/assignmentPresetNodes',
        }),
    },
    methods: {
        ...mapActions({
            updateAssignment: 'assignment/update',
        }),
        ...mapMutations({
            setModeToEdit: 'assignmentEditor/SET_ACTIVE_COMPONENT_MODE_TO_EDIT',
            setModeToRead: 'assignmentEditor/SET_ACTIVE_COMPONENT_MODE_TO_READ',
        }),
    },
}
</script>

<style>

</style>
