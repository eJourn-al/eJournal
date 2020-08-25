<template>
    <b-card
        :class="$root.getBorderClass($route.params.cID)"
        class="no-hover"
    >
        <h2 class="theme-h2">
            End of assignment
        </h2>
        <hr class="full-width"/>
        <b v-if="assignment.due_date">
            <span v-if="new Date() > new Date(assignment.due_date) && !assignment.lock_date">
                The due date for this assignment has passed.<br/>
            </span>
            Due date: {{ $root.beautifyDate(assignment.due_date) }}<br/>
        </b>
        <b v-if="assignment.lock_date">
            <span v-if="new Date(assignment.lock_date) < new Date()">
                This assignment has been locked<br/>
            </span>
            Lock date: {{ $root.beautifyDate(assignment.lock_date) }}<br/>
        </b>
        <b v-else-if="!assignment.due_date">
            There is no due date set for this assignment.
        </b>
    </b-card>
</template>

<script>
export default {
    props: ['assignment'],
}
</script>
