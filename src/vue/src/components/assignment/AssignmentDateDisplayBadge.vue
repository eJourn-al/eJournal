<template>
    <b-badge
        v-if="date"
        v-b-tooltip.hover
        class="background-blue align-middle mr-1"
        :title="`This assignment ${assignment.due_date ? 'is due' : 'locks'} on ${$root.beautifyDate(date)}`"
        pill
    >
        <icon
            v-if="assignment.due_date"
            name="clock"
            scale="0.8"
            class="shift-up-2"
        />
        <icon
            v-else
            name="lock"
            scale="0.8"
            class="shift-up-2"
        />
        {{ $root.beautifyDate(date) }}
    </b-badge>
</template>

<script>

export default {
    props: {
        assignment: {
            required: true,
            type: Object,
        },
    },
    computed: {
        date () {
            if (!(this.assignment.due_date || this.assignment.lock_date)) { return null }
            return (this.assignment.due_date) ? this.assignment.due_date : this.assignment.lock_date
        },
    },
}
</script>
