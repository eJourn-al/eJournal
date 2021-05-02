<template>
    <div class="p-2 background-light-grey round-border d-inline-block small">
        <b class="mr-1">Due</b>
        <span v-if="subject.due_date">
            {{ $root.beautifyDate(subject.due_date) }}
        </span>
        <span v-else>
            No due date set
        </span>
        <template v-if="deadlineRange">
            <b class="ml-2 mr-1">Available</b>
            {{ deadlineRange }}
        </template>
    </div>
</template>

<script>
export default {
    props: {
        subject: {
            required: true,
        },
    },
    computed: {
        deadlineRange () {
            const unlockDate = this.$root.beautifyDate(this.subject.unlock_date)
            const lockDate = this.$root.beautifyDate(this.subject.lock_date)

            if (unlockDate && lockDate) {
                return `from ${unlockDate} until ${lockDate}`
            } else if (unlockDate) {
                return `from ${unlockDate}`
            } else if (lockDate) {
                return `until ${lockDate}`
            }

            return ''
        },
    },
}
</script>
