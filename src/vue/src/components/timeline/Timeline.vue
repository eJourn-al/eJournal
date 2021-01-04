<!--
    Timeline component. Handles the prop connection with parent, as well as any
    functionality involving the list (ie. showing the list,
    passing selected state)

    Nodes are accessed via array index. Some 'virtual' nodes exists, these are not part of the nodes array.
        - Start of assignment: -1
        - Add node
            - Virtual when adding a preset to the format: nodes.length
              (not virtual when adding an entry to the timeline, but has NO nID)
        - End of assignment: nodes.length + 1
    Passed property nodes can consist of two types:
        - Preset nodes (edit = true) (format edit view)
        - nodes (journal view)
-->

<template>
    <div class="timeline-container">
        <b-collapse id="timeline-outer">
            <div
                ref="scd"
                class="timeline-inner"
            >
                <theme-select
                    v-if="$store.getters['category/assignmentCategories']"
                    v-model="filteredCategories"
                    class="mt-2"
                    label="name"
                    trackBy="id"
                    :options="$store.getters['category/assignmentCategories']"
                    :multiple="true"
                    :searchable="true"
                    :multiSelectText="`${filteredCategories.length > 1 ? 'categories' : 'category'}`"
                    placeholder="Filter By Category"
                    @input="filterByCategory"
                />

                <div
                    v-b-toggle="($root.lgMax) ? 'timeline-outer' : null"
                    :target="($root.lgMax) ? 'timeline-outer': null"
                    aria-expanded="false"
                    aria-controls="timeline-outer"
                >
                    <timeline-nodes
                        :assignment="assignment"
                        :edit="edit"
                        :nodes="filteredNodes"
                        :allNodes="nodes"
                        :selected="mappedSelected"
                        @select-node="mapAndEmitSelectedNode"
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
import TimelineNodes from '@/components/timeline/TimelineNodes.vue'

export default {
    components: {
        TimelineNodes,
    },
    props: {
        /* Boolean used to indicate the assignment format is being edited, new preset nodes can be inserted
         * which will not yet be saved / have an id.
         * Entries are created one at a time and are always inserted after save (with id) */
        edit: {
            default: false,
            type: Boolean,
        },
        /* Array of node (edit = false) or preset node (edit = true) objects  */
        nodes: {
            required: true,
            type: Array,
        },
        /* Index of the selected node as part of the full (non filtered) nodes array */
        selected: {
            required: true,
            type: Number,
        },
        assignment: {
            required: true,
            type: Object,
        },
    },
    data () {
        return {
            filteredNodes: [],
            startOfAssignmentNodeIndexSymbol: -1,
            mappedSelected: this.startOfAssignmentNodeIndexSymbol,
        }
    },
    computed: {
        filteredCategories: {
            set (value) { this.$store.commit('category/setFilteredCategories', value) },
            get () { return this.$store.getters['category/filteredCategories'] },
        },
        /* Selected node is actually part of the node array property, see virtual nodes in header */
        selectedNodeIsActualObject () {
            return this.selected >= 0 && this.selected < this.nodes.length
        },
    },
    watch: {
        /* Selected is the index of the selected node part of the full nodes array, which excludes the virtual nodes
         * assignment info (-1) and end of assignment (nodes.length + 1)
         * The selected node index needs to be mapped to the correct index of the filtered nodes array */
        selected (val) {
            if (val < 0) { // Virtual node: assignment details
                this.mappedSelected = val
            } else if (val === this.nodes.length) { // Virtual node: add node (only virtual in (format) edit mode...)
                this.mappedSelected = val
            } else if (val === this.nodes.length + 1) { // Virtual node: end of assignment
                this.mappedSelected = val
            /* Dealing with an actual node */
            } else {
                const selectedNode = this.nodes[val]
                this.mappedSelected = this.findNodeIndex(this.filteredNodes, selectedNode)
            }
        },
        /* Nodes can be added or removed from the parent (e.g. delete or add)
         * Just filter the new nodes again to remain synced */
        nodes () {
            this.filterByCategory(this.filteredCategories)
        },
    },
    created () {
        this.filteredNodes = this.nodes
        this.mappedSelected = this.selected
    },
    methods: {
        mapAndEmitSelectedNode (index) {
            this.$emit('select-node', this.mappedNodesIndex(index))
        },
        /* Maps the index of the filtered nodes to its corresponding index in the list of all nodes.
         * This allows the existing emit structure to continue without refactor. */
        mappedNodesIndex (index) {
            /* Working with virtual nodes (start, end of assignment)
             * NOTE: The add node does exist, and is simply added in the backend
             * (only for journal view not format edit). */
            if (index < 0 || index >= this.filteredNodes.length) {
                return index
            } else {
                return this.findNodeIndex(this.nodes, this.filteredNodes[index])
            }
        },
        hasCategory (categories, filters) {
            return categories.some(category => filters.find(filteredCategory => category.id === filteredCategory.id))
        },
        findNodeIndex (nodes, node) {
            /* When editing the timeline (edit = true) we are working with preset nodes directly
             * Otherwise we are working with a timeline consisting of normal nodes */
            const idKey = (this.edit) ? 'id' : 'nID'

            return nodes.findIndex(elem => elem[idKey] === node[idKey])
        },
        /* Next to filtering the nodes based on the selected categories, also keeps the selected node index in sync.
         * If a node was selected which is no longer part of the filtered nodes, selects the start of the assignment. */
        filterByCategory (filters) {
            let selectedNode

            if (this.selectedNodeIsActualObject) {
                selectedNode = this.nodes[this.selected]
            }

            if (!filters.length) {
                this.filteredNodes = this.nodes
            } else {
                this.filteredNodes = this.nodes.filter((node) => {
                    if (node.type === 'e') {
                        return this.hasCategory(node.entry.categories, filters)
                    } else if (node.type === 'd') {
                        if ('entry' in node && node.entry) {
                            return this.hasCategory(node.entry.categories, filters)
                        /* Deadline without entry, filter on template categories */
                        } else if (node.template.categories) {
                            return this.hasCategory(node.template.categories, filters)
                        }
                    } else if (node.type === 'a') {
                        return true
                    }
                    return false
                })
            }

            if (this.selectedNodeIsActualObject) {
                this.mappedSelected = this.findNodeIndex(this.filteredNodes, selectedNode)

                if (this.filteredNodes.indexOf(selectedNode) === -1) {
                    this.$emit('select-node', this.startOfAssignmentNodeIndexSymbol)
                }
            }
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
