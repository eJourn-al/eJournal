<!--
    Component representing a node in the Timeline.
    Handles the compositing of circle and date subcomponents, its own style
    depending on state given by parent, and passes relevant parts of the state
    to the subcomponents.
-->

<template>
    <b-row class="node-container">
        <b-col
            cols="4"
            class="d-flex h-100 align-items-center justify-content-center"
        >
            <div
                :class="timeLineClass"
                class="time-line"
            />
            <timeline-node-circle
                :node="node"
                class="position-absolute"
                @click.native="setCurrentNode(node)"
            />
        </b-col>
        <b-col
            cols="8"
            class="d-flex h-100 align-items-center"
        >
            <timeline-node-info :node="node"/>
        </b-col>
    </b-row>
</template>

<script>
import timelineNodeCircle from '@/components/timeline/TimelineNodeCircle.vue'
import timelineNodeInfo from '@/components/timeline/TimelineNodeInfo.vue'

import { mapGetters, mapMutations } from 'vuex'

export default {
    components: {
        timelineNodeInfo,
        timelineNodeCircle,
    },
    props: {
        node: {
            required: true,
            type: Object,
        },
    },
    computed: {
        ...mapGetters({
            startNode: 'timeline/startNode',
            addNode: 'timeline/addNode',
            endNode: 'timeline/endNode',
        }),
        timeLineClass () {
            return {
                top: this.node === this.startNode,
                bottom: this.node === this.endNode,
            }
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
.node-container
    height: 100px
    .time-line
        position: absolute
        width: 5px
        background-color: $theme-dark-grey
        height: 100px
        &.top
            height: 50px
            top: 50px
        &.bottom
            height: 50px
            bottom: 50px
</style>
