<template>
    <b-card
        :class="$root.getBorderClass($route.params.cID)"
        class="no-hover"
    >
        <b-row
            no-gutters
            class="multi-form"
        >
            <span class="theme-h2">
                End of assignment
            </span>

            <slot name="edit-button"/>
        </b-row>

        <hr/>

        <span
            v-if="assignment.due_date"
            class="text-grey"
        >
            <span v-if="new Date() > new Date(assignment.due_date) && !assignment.lock_date">
                The due date for this assignment has passed<br/>
            </span>
            Due date: {{ $root.beautifyDate(assignment.due_date) }}<br/>
        </span>
        <span
            v-if="assignment.lock_date"
            class="text-grey"
        >
            <span v-if="new Date(assignment.lock_date) < new Date()">
                This assignment has been locked<br/>
            </span>
            Lock date: {{ $root.beautifyDate(assignment.lock_date) }}<br/>
        </span>
        <span
            v-else-if="!assignment.due_date"
            class="text-grey"
        >
            There is no due date set for this assignment
        </span>
    </b-card>
</template>

<script>
export default {
    props: ['assignment'],
}
</script>
