<!--
    Mini component representing the circle for a node in the Timeline.
    Handles its own style depending on a state given by parent.
-->

<template>
    <div class="timeline-node-circle-border">
        <div
            :title="nodeTitle"
            :class="nodeClass"
            class="timeline-node-circle unselectable"
            data-toggle="tooltip"
        >
            <icon
                v-if="node.type !== 'p'"
                :name="iconName"
                :class="iconClass"
                :scale="iconScale"
            />
            <div
                v-else
                class="timeline-node-circle-text"
            >
                {{ node.target }}
            </div>
        </div>
    </div>
</template>

<script>
export default {
    props: ['node', 'selected', 'edit'],
    computed: {
        nodeClass () {
            return {
                'enc-start': this.node.type === 's',
                'enc-end': this.node.type === 'n',
                'enc-entry': this.node.type === 'e',
                'enc-deadline': this.node.type === 'd',
                'enc-progress': this.node.type === 'p',
                'enc-add': this.node.type === 'a',
                'enc-selected': this.selected,
            }
        },
        iconName () {
            switch (this.nodeState()) {
            case 'graded':
                return 'check'
            case 'failed':
            case 'overdue':
                return 'clock'
            case 'awaiting_grade':
                return 'hourglass-half'
            case 'needs_grading':
                return 'exclamation'
            case 'needs_publishing':
                return 'eye-slash'
            case 'add':
                return 'plus'
            case 'start':
                return 'info-circle'
            case 'end':
                return 'flag-checkered'
            default:
                return 'calendar'
            }
        },
        nodeTitle () {
            switch (this.nodeState()) {
            case 'graded':
                return 'Graded'
            case 'failed':
                return 'Not submitted'
            case 'overdue':
                return 'Due date passed'
            case 'awaiting_grade':
                return 'Awaiting grade'
            case 'needs_grading':
                return 'Needs grading'
            case 'needs_publishing':
                return 'Awaiting publishment'
            case 'add':
                if (this.edit) {
                    return 'Add new preset'
                } else {
                    return 'Add new entry'
                }
            case 'start':
            case 'end':
                return 'Assignment details'
            default:
                return 'Deadline'
            }
        },
        iconClass () {
            switch (this.nodeState()) {
            case 'graded':
                return 'fill-green'
            case 'overdue':
                return 'fill-orange'
            case 'failed':
                return 'fill-red'
            case 'start':
            case 'end':
            case 'add':
                return 'fill-white'
            default:
                if (this.selected) { return 'fill-white' }
                return 'fill-grey'
            }
        },
        iconScale () {
            if (this.node.type === 'a') {
                if (this.selected) {
                    return '1.5'
                } else {
                    return '1'
                }
            }
            if (this.selected) {
                return '2'
            } else {
                return '1.5'
            }
        },
    },
    methods: {
        dueDateHasPassed () {
            const currentDate = new Date()
            const dueDate = new Date(this.node.due_date)

            return currentDate > dueDate
        },
        lockDateHasPassed () {
            if (!this.node.lock_date) {
                return false
            }

            const currentDate = new Date()
            const lockDate = new Date(this.node.lock_date)

            return currentDate > lockDate
        },
        nodeState () {
            if (this.node.type === 's') {
                return 'start'
            } else if (this.node.type === 'n') {
                return 'end'
            } else if (this.node.type === 'a') {
                return 'add'
            } else if (this.edit || this.node.type === 'p') {
                return ''
            }

            const entry = this.node.entry
            const isGrader = this.$hasPermission('can_grade')

            if (entry && entry.grade && entry.grade.published) {
                return 'graded'
            } else if (!entry && this.lockDateHasPassed()) {
                return 'failed'
            } else if (!entry && this.dueDateHasPassed()) {
                return 'overdue'
            } else if (!entry && !this.dueDateHasPassed()) {
                return 'empty'
            } else if (!isGrader && entry && !entry.grade) {
                return 'awaiting_grade'
            } else if (isGrader && entry && (!entry.grade || !entry.grade.grade)) {
                return 'needs_grading'
            } else if (isGrader && entry && entry.grade && !entry.grade.published) {
                return 'needs_publishing'
            }

            return ''
        },
    },
}
</script>

<style lang="sass">
@import '~sass/modules/colors.sass'
@import '~sass/partials/shadows.sass'

.timeline-node-circle-border
    border-radius: 50% !important
    padding: 5px

.timeline-node-circle
    @extend .theme-shadow
    width: 55px
    height: 55px
    border-radius: 50% !important
    display: flex
    align-items: center
    justify-content: center
    transition: all 0.3s cubic-bezier(.25,.8,.25,1)
    &:not(.enc-selected)
        cursor: pointer
    &.enc-selected
        width: 75px
        height: 75px
    &.enc-add
        width: 45px
        height: 45px
    &.enc-selected.enc-add
        width: 55px
        height: 55px
    &.enc-entry, &.enc-deadline
        background-color: white
    &.enc-start
        background-color: $theme-green
    &.enc-end
        background-color: $theme-green
    &.enc-add
        background-color: $theme-blue
    &.enc-progress
        background-color: $theme-orange
    &.enc-selected
        background-color: $theme-dark-blue
    svg
        transition: all 0.3s cubic-bezier(.25,.8,.25,1)
    .timeline-node-circle-text
        color: white
        font-family: 'Roboto Condensed', sans-serif
        font-weight: bold
        font-size: 1.5em
</style>
