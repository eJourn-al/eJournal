<!--
    Timeline component. Handles the prop connection with parent, as well as any
    functionality involving the list (ie. showing the list,
    passing selected state)
-->

<template>
    <div class="timeline-container">
        <b-collapse id="timeline-outer">
            <div
                ref="scd"
                class="timeline-inner"
            >
                <div
                    v-if="$root.lgMax"
                    v-b-toggle.timeline-outer
                    target="timeline-outer"
                    aria-expanded="false"
                    aria-controls="timeline-outer"
                >
                    <timeline-node
                        :index="-1"
                        :node="{
                            'type': 's'
                        }"
                        :selected="isSelected(-1)"
                        :edit="edit"
                        @select-node="$emit('select-node', $event)"
                    />
                    <timeline-node
                        v-for="(node, index) in nodes"
                        :key="node.id"
                        :index="index"
                        :node="node"
                        :selected="isSelected(index)"
                        :edit="edit"
                        @select-node="$emit('select-node', $event)"
                    />
                    <timeline-node
                        v-if="edit"
                        :index="nodes.length"
                        :node="{
                            'type': 'a'
                        }"
                        :selected="isSelected(nodes.length)"
                        :edit="edit"
                        @select-node="$emit('select-node', $event)"
                    />
                    <timeline-node
                        :index="nodes.length + 1"
                        :last="true"
                        :node="{
                            'type': 'n',
                            'due_date': assignment.due_date
                        }"
                        :selected="isSelected(nodes.length + 1)"
                        :edit="edit"
                        @select-node="$emit('select-node', $event)"
                    />
                </div>
                <div v-else>
                    <timeline-node
                        :index="-1"
                        :node="{
                            'type': 's'
                        }"
                        :selected="isSelected(-1)"
                        :edit="edit"
                        @select-node="$emit('select-node', $event)"
                    />
                    <timeline-node
                        v-for="(node, index) in nodes"
                        :key="node.id"
                        :index="index"
                        :node="node"
                        :selected="isSelected(index)"
                        :edit="edit"
                        @select-node="$emit('select-node', $event)"
                    />
                    <timeline-node
                        v-if="edit"
                        :index="nodes.length"
                        :node="{
                            'type': 'a'
                        }"
                        :selected="isSelected(nodes.length)"
                        :edit="edit"
                        @select-node="$emit('select-node', $event)"
                    />
                    <timeline-node
                        :index="nodes.length + 1"
                        :last="true"
                        :node="{
                            'type': 'n',
                            'due_date': assignment.due_date
                        }"
                        :selected="isSelected(nodes.length + 1)"
                        :edit="edit"
                        @select-node="$emit('select-node', $event)"
                    />
                </div>
            </div>
        </b-collapse>

        <div
            id="timeline-toggle"
            v-b-toggle.timeline-outer
            target="timeline-outer"
            aria-expanded="false"
            aria-controls="timeline-outer"
        >
            <span class="timeline-outer__icon timeline-outer__icon--open">
                <icon
                    class="collapse-icon"
                    name="list-ul"
                    scale="1.75"
                />
            </span>
            <span class="timeline-outer__icon timeline-outer__icon--close">
                <icon
                    class="collapse-icon"
                    name="caret-up"
                    scale="1.75"
                />
            </span>
        </div>
    </div>
</template>

<script>
import timelineNode from '@/components/timeline/TimelineNode.vue'

export default {
    components: {
        timelineNode,
    },
    props: ['selected', 'nodes', 'edit', 'assignment'],
    methods: {
        isSelected (id) {
            return id === this.selected
        },
    },
}
</script>

<style lang="sass">
.timeline-container
    @include lg-max
        text-align: center
    @include xl
        height: 100%

.timeline-inner::-webkit-scrollbar
    display: none

#timeline-outer
    overflow: hidden
    height: 100%

@include xl
    #timeline-outer[style]
        display: block !important

.timeline-inner
    height: 100%
    overflow-y: scroll
    overflow-x: hidden
    padding-right: 40px
    margin-right: -20px
    padding-left: 5px
    @include lg-max
        height: 50vh

#timeline-toggle
    display: none

@include lg-max
    /* Handles changing of the button icon. */
    [aria-expanded="false"] .timeline-outer__icon--open
        display: block
        text-align: center

    [aria-expanded="false"] .timeline-outer__icon--close
        display: none
        text-align: center

    [aria-expanded="true"] .timeline-outer__icon--open
        display: none
        text-align: center

    [aria-expanded="true"] .timeline-outer__icon--close
        display: block
        text-align: center

    #timeline-toggle
        display: block
        border: 0px
        padding: 10px 0px
        border-radius: 40px !important
        background-color: $theme-blue !important
        &:hover
            background-color: $theme-blue !important
            cursor: pointer
        .collapse-icon
            display: block
            margin-left: auto
            margin-right: auto
            fill: white
</style>
