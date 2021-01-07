<template>
    <b-card :class="$root.getBorderClass(assignment.id)">
        <slot class="float-right"/>
        <h2 class="theme-h2">
            {{ assignment.name }}
        </h2>
        <b-badge
            v-if="!assignment.lti_couples > 0"
            v-b-tooltip:hover="'Linked via LTI'"
            pill
            variant="primary"
            class="align-middle mr-1"
        >
            LTI
        </b-badge>
        <b-badge
            v-if="!assignment.is_published"
            v-b-tooltip:hover="'Not visible to students: click to edit'"
            pill
            class="align-middle"
        >
            Unpublished
        </b-badge>

        <assignment-date-display-badge :assignment="assignment"/>
    </b-card>
</template>

<script>
import AssignmentDateDisplayBadge from '@/components/assignment/AssignmentDateDisplayBadge.vue'

export default {
    components: {
        AssignmentDateDisplayBadge,
    },
    props: ['assignment', 'uniqueName'],
}
</script>
