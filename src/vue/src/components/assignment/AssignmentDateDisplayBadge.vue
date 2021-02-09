<template>
    <b-badge
        v-if="date"
        class="background-medium-grey align-middle mr-1"
        pill
    >
        <span class="text-grey">
            <icon
                name="clock"
                scale="0.8"
                class="fill-grey shift-up-2"
            />
            {{ $root.beautifyDate(date) }}
        </span>
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
