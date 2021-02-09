<template>
    <div>
        <timeline-node
            :index="-1"
            :node="{ 'type': 's' }"
            :selected="isSelected(-1)"
            :edit="edit"
            v-on="$listeners"
        />

        <timeline-node
            v-for="(node, index) in nodes"
            :key="node.id"
            :index="index"
            :node="node"
            :selected="isSelected(index)"
            :edit="edit"
            v-on="$listeners"
        />

        <timeline-node
            v-if="edit"
            :index="allNodes.length"
            :node="{ 'type': 'a' }"
            :selected="isSelected(allNodes.length)"
            :edit="edit"
            v-on="$listeners"
        />

        <timeline-node
            :index="allNodes.length + 1"
            :last="true"
            :node="{
                'type': 'n',
                'due_date': assignment.due_date
            }"
            :selected="isSelected(allNodes.length + 1)"
            :edit="edit"
            v-on="$listeners"
        />
    </div>
</template>

<script>
import timelineNode from '@/components/timeline/TimelineNode.vue'

export default {
    name: 'TimelineNodes',
    components: {
        timelineNode,
    },
    props: {
        edit: {
            default: false,
            type: Boolean,
        },
        nodes: {
            required: true,
            type: Array,
        },
        allNodes: {
            required: true,
            type: Array,
        },
        selectedIndex: {
            required: true, /* Can be null, indicating nothing should be selected */
        },
        assignment: {
            required: true,
            type: Object,
        },
    },
    methods: {
        isSelected (index) {
            return index === this.selectedIndex
        },
    },
}
</script>
