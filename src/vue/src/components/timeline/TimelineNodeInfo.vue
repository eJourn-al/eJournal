<!--
    Mini component representing the date for a node in the Timeline.
    Handles its own style depending on a state given by parent.
-->

<template>
    <span
        :class="{'selected': node === currentNode}"
        class="node-info"
    >
        <span
            v-if="nodeTitle"
            class="node-title max-one-line"
            :class="{ dirty: dirty }"
            @click="setCurrentNode(node); $root.$emit('bv::toggle::collapse', 'timeline-container')"
        >
            <icon
                v-if="new Date(nodeDate) > new Date()"
                v-b-tooltip:hover="'Upcoming deadline'"
                :name="nodeIcon"
                class="mb-1 mr-1"
            />
            {{ nodeTitle }}
        </span>

        <category-display
            :id="`timeline-node-${node.id}-categories`"
            :categories="nodeCategories"
            :compact="true"
            class="small"
        />
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
import CategoryDisplay from '@/components/category/CategoryDisplay.vue'

import { mapGetters, mapMutations } from 'vuex'

export default {
    components: {
        CategoryDisplay,
    },
    props: {
        node: {
            type: Object,
            required: true,
        },
    },
    computed: {
        ...mapGetters({
            assignment: 'assignment/assignment',
            isPresetNodeDirty: 'assignmentEditor/isPresetNodeDirty',
            isAssignmentDetailsDirty: 'assignmentEditor/isAssignmentDetailsDirty',
            currentNode: 'timeline/currentNode',
            endNode: 'timeline/endNode',
        }),
        nodeTitle () {
            if (this.node.entry) {
                return this.node.entry.title
            }

            switch (this.node.type) {
            case 'd':
            case 'p':
                return this.node.display_name
            case 'n':
                return 'End of assignment'
            case 's':
                return 'Assignment details'
            case 'a':
                return `New ${this.$route.name === 'Journal' ? 'entry' : 'deadline'}`
            default:
                return null
            }
        },
        nodeCategories () {
            if (this.node.entry) {
                return this.node.entry.categories
            } else if (this.node.type === 'd') {
                return this.node.template.categories
            }

            return []
        },
        nodeDate () {
            if (this.node.entry && this.node.entry.creation_date) {
                return this.node.entry.creation_date
            } else if (this.node.due_date) {
                return this.node.due_date
            } else if (this.node === this.endNode) {
                return this.assignment.due_date
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
                return `Available: from ${unlockDate} until ${lockDate}`
            } else if (unlockDate) {
                return `Available: from ${unlockDate}`
            } else if (lockDate) {
                return `Available: until ${lockDate}`
            }

            return ''
        },
        dirty () {
            if (this.$route.name !== 'AssignmentEditor') { return false }

            if (this.node.type === 's') {
                return this.isAssignmentDetailsDirty(this.assignment)
            } else if (this.node.type === 'd' || this.node.type === 'p') {
                return this.isPresetNodeDirty(this.node)
            }

            return false
        },
    },
    methods: {
        ...mapMutations({
            setCurrentNode: 'timeline/SET_CURRENT_NODE',
        }),
    },
}
</script>

<style lang="sass">
.node-info
    width: 100%
    user-select: none
    &:not(.selected)
        color: grey
        .node-title:hover
            cursor: pointer
            color: $text-color
    .node-title
        font-weight: bold
    .node-date
        font-size: 0.9em
</style>
