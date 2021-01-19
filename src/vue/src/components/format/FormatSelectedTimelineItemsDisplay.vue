<template>
    <div>
        <b-card
            v-if="currentNode === -1"
            :class="$root.getBorderClass($route.params.cID)"
            class="no-hover"
        >
            <assignment-details
                ref="assignmentDetails"
                :class="{ 'input-disabled' : saveRequestInFlight }"
                :assignmentDetails="assignmentDetails"
                :presetNodes="presets"
            />
        </b-card>

        <format-preset-node-card
            v-else-if="presets.length > 0 && currentNode !== -1 && currentNode < presets.length"
            :key="`preset-node-${currentNode}`"
            :class="{ 'input-disabled' : saveRequestInFlight }"
            :currentPreset="presets[currentNode]"
            :templates="templates"
            :assignmentDetails="assignmentDetails"
            @delete-preset="deletePreset"
            @change-due-date="sortPresets"
            @new-template="newTemplateInPreset"
        />

        <format-add-preset-node
            v-else-if="currentNode === presets.length"
            :class="{ 'input-disabled' : saveRequestInFlight }"
            :templates="templates"
            :assignmentDetails="assignmentDetails"
            @add-preset="addPreset"
            @new-template="newTemplateInPreset"
        />

        <b-card
            v-else-if="currentNode === presets.length + 1"
            class="no-hover"
            :class="$root.getBorderClass($route.params.cID)"
        >
            <h2 class="theme-h2">
                End of assignment
            </h2>
            <p>This is the end of the assignment.</p>
        </b-card>
    </div>
</template>

<script>
import AssignmentDetails from '@/components/assignment/AssignmentDetails.vue'
import FormatAddPresetNode from '@/components/format/FormatAddPresetNode.vue'
import FormatPresetNodeCard from '@/components/format/FormatPresetNodeCard.vue'

export default {
    name: 'FormatSelectedTimelineItemsDisplay',
    components: {
        AssignmentDetails,
        FormatPresetNodeCard,
        FormatAddPresetNode,
    },
}
</script>

<style>

</style>
