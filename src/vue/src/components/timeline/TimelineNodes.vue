<template>
    <div>
        <timeline-node
            :node="startNode"
        />

        <timeline-node
            v-for="node in allNodes"
            v-show="filteredNodes.includes(node)"
            :key="node.id"
            :node="node"
        />

        <!-- Add node is only serialized in the backend for a journal view, but not for the assignment editor -->
        <timeline-node
            v-if="$route.name === 'AssignmentEditor'"
            :node="addNode"
        />

        <timeline-node
            :node="endNode"
        />
    </div>
</template>

<script>
import timelineNode from '@/components/timeline/TimelineNode.vue'

import { mapGetters } from 'vuex'

export default {
    name: 'TimelineNodes',
    components: {
        timelineNode,
    },
    props: {
        filteredNodes: {
            required: true,
            type: Array,
        },
        allNodes: {
            required: true,
            type: Array,
        },
    },
    computed: {
        ...mapGetters({
            startNode: 'timeline/startNode',
            addNode: 'timeline/addNode',
            endNode: 'timeline/endNode',
        }),
    },
}
</script>
