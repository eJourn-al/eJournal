<!--
    Mini component representing the date for a node in the Timeline.
    Handles its own style depending on a state given by parent.
-->

<template>
    <span
        :class="{'selected': selected}"
        class="node-info"
    >
        <span
            v-if="nodeTitle"
            class="node-title max-one-line"
        >
            <icon
                v-if="new Date(nodeDate) > new Date()"
                v-b-tooltip:hover="'Upcoming deadline'"
                :name="nodeIcon"
                class="mb-1 mr-1"
            />
            {{ nodeTitle }}
        </span>

        <span
            v-if="nodeDate"
            v-b-tooltip:hover="deadlineRange"
            class="node-date"
        >
            {{ $root.beautifyDate(nodeDate) }}
        </span>
    </span>
</template>

<script>
export default {
    props: ['node', 'selected'],
    computed: {
        nodeTitle () {
            switch (this.node.type) {
            case 'e':
                return this.node.entry.title
            case 'd':
                return this.node.template.name
            case 'p':
                return 'Progress goal'
            case 'n':
                return 'End of assignment'
            case 's':
                return 'Assignment details'
            default:
                return null
            }
        },
        nodeDate () {
            if (this.node.entry && this.node.entry.creation_date) {
                return this.node.entry.creation_date
            } else if (this.node.due_date) {
                return this.node.due_date
            } else {
                return null
            }
        },
        nodeIcon () {
            switch (this.node.type) {
            case 'd':
                return 'calendar'
            case 'p':
            case 'n':
                return 'flag-checkered'
            default:
                return null
            }
        },
        deadlineRange () {
            const unlockDate = this.$root.beautifyDate(this.node.unlock_date)
            const lockDate = this.$root.beautifyDate(this.node.lock_date)

            if (unlockDate && lockDate) {
                return `Available from ${unlockDate} until ${lockDate}`
            } else if (unlockDate) {
                return `Available from ${unlockDate}`
            } else if (lockDate) {
                return `Available until ${lockDate}`
            }

            return ''
        },
    },
}
</script>

<style lang="sass">
.node-info
    text-align: right
    width: 100%
    user-select: none
    &.selected
        cursor: auto
        opacity: 1
    &:not(.selected)
        opacity: 0.5
    .node-title
        font-weight: bold
        color: grey
    .node-date
        font-family: 'Roboto Condensed'
        font-size: 0.9em
        color: grey
</style>
