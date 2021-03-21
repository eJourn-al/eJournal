<template>
    <div>
        <template v-if="selectedTimelineElementIndex === -1">
            <assignment-start-read-mode v-if="readMode"/>
            <assignment-details-edit v-else/>
        </template>

        <template v-else-if="selectedTimelineElementIndex >= 0 && selectedTimelineElementIndex <= presetNodes.length">
            <preset-node-read-mode v-if="readMode"/>
            <preset-node-edit
                v-else
                :key="`preset-node-${presetNode.id}-edit`"
            />
        </template>

        <template v-else-if="selectedTimelineElementIndex === presetNodes.length + 1">
            <assignment-end-read-mode v-if="readMode"/>
            <assignment-details-edit v-else/>
        </template>
    </div>
</template>

<script>
import AssignmentDetailsEdit from
    '@/components/assignment_editor/timeline_controlled/assignment/AssignmentDetailsEdit.vue'
import AssignmentEndReadMode from
    '@/components/assignment_editor/timeline_controlled/assignment/AssignmentEndReadMode.vue'
import AssignmentStartReadMode
    from '@/components/assignment_editor/timeline_controlled/assignment/AssignmentStartReadMode.vue'
import PresetNodeEdit from '@/components/assignment_editor/timeline_controlled/preset_node/PresetNodeEdit.vue'
import PresetNodeReadMode from '@/components/assignment_editor/timeline_controlled/preset_node/PresetNodeReadMode.vue'

import { mapGetters } from 'vuex'

export default {
    name: 'SelectedTimelineComponentSwitch',
    components: {
        AssignmentDetailsEdit,
        AssignmentEndReadMode,
        AssignmentStartReadMode,
        PresetNodeEdit,
        PresetNodeReadMode,
    },
    computed: {
        ...mapGetters({
            readMode: 'assignmentEditor/readMode',
            selectedTimelineElementIndex: 'assignmentEditor/selectedTimelineElementIndex',
            presetNodes: 'presetNode/assignmentPresetNodes',
            presetNode: 'assignmentEditor/selectedPresetNode',
        }),
    },
}
</script>
