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
        <b-badge
            v-if="assignment.due_date || assignment.lock_date"
            pill
            class="background-medium-grey align-middle mr-1"
        >
            <span
                v-if="assignment.due_date"
                class="text-grey"
            >
                <icon
                    name="clock"
                    scale="0.8"
                    class="fill-grey shift-up-2"
                />
                {{ $root.beautifyDate(assignment.due_date) }}
            </span>
            <span
                v-else-if="assignment.lock_date"
                class="text-grey"
            >
                <icon
                    name="lock"
                    scale="0.8"
                    class="fill-grey shift-up-2"
                />
                {{ $root.beautifyDate(assignment.lock_date) }}
            </span>
        </b-badge>
    </b-card>
</template>

<script>

export default {
    props: ['assignment', 'uniqueName'],
}
</script>
