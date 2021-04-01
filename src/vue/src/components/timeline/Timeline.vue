<!--
    Timeline component. Responsible for displaying, navigating, and filtering the timeline.

    Node navigation occurs via setting the 'currentNode' in the timeline store module.
    Some nodes exists which have no underlying DB representation, these are not part of the nodes array.
        - Start of assignment
        - Add node
            - Virtual when adding a preset to the assignment: nodes.length
              (not virtual when adding an entry to the timeline, but has NO id)
        - End of assignment
    Passed property nodes can consist of two types:
        - Preset nodes (assignment editor view)
        - nodes (journal view)
-->

<template>
    <div>
        <b-collapse id="timeline-container">
            <h3 class="theme-h3 mb-1 mr-2">
                Timeline
            </h3>

            <b-dropdown
                v-if="assignmentHasCategories"
                class="timeline-filter"
                noCaret
                variant="link"
            >
                <template #button-content>
                    <b-button
                        pill
                        class="filter-button"
                        :class="{
                            'blue-filled-button': filteredCategories.length > 0,
                            'grey-filled-button': filteredCategories.length === 0,
                        }"
                    >
                        <icon name="eye"/>
                        Filter
                    </b-button>
                </template>
                <category-select
                    v-model="filteredCategories"
                    :options="$store.getters['category/assignmentCategories']"
                    :multiple="true"
                    :searchable="true"
                    :multiSelectText="`${filteredCategories.length > 1 ? 'categories' : 'category'}`"
                    @input="filterByCategory"
                />
            </b-dropdown>

            <category-display
                :id="'timeline-filter-categories'"
                :categories="filteredCategories"
            />

            <template
                v-b-toggle="($root.lgMax) ? 'timeline-container' : null"
                :target="($root.lgMax) ? 'timeline-container': null"
                aria-expanded="false"
                aria-controls="timeline-container"
            >
                <timeline-nodes
                    :filteredNodes="filteredNodes"
                    :allNodes="nodes"
                />
            </template>
        </b-collapse>

        <div
            id="timeline-toggle"
            v-b-toggle.timeline-container
            target="timeline-container"
            aria-expanded="false"
            aria-controls="timeline-container"
        >
            <span class="timeline-container__icon timeline-container__icon--open">
                <icon
                    class="collapse-icon"
                    name="list-ul"
                    scale="1.75"
                />
            </span>
            <span class="timeline-container__icon timeline-container__icon--close">
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
import CategoryDisplay from '../category/CategoryDisplay.vue'
import CategorySelect from '@/components/category/CategorySelect.vue'
import TimelineNodes from '@/components/timeline/TimelineNodes.vue'

import { mapGetters, mapMutations } from 'vuex'

export default {
    components: {
        CategoryDisplay,
        CategorySelect,
        TimelineNodes,
    },
    props: {
        /* Array of nodes (journal view) or preset nodes (assignment editor view) */
        nodes: {
            required: true,
            type: Array,
        },
        assignment: {
            required: true,
            type: Object,
        },
    },
    data () {
        return {
            filteredNodes: [],
        }
    },
    computed: {
        ...mapGetters({
            assignmentHasCategories: 'category/assignmentHasCategories',
            currentNode: 'timeline/currentNode',
            startNode: 'timeline/startNode',
        }),
        filteredCategories: {
            set (value) { this.$store.commit('timeline/SET_FILTERED_CATEGORIES', value) },
            get () { return this.$store.getters['timeline/filteredCategories'] },
        },
    },
    watch: {
        /* Nodes can be added or removed from the parent (e.g. delete or add)
         * Just filter the new nodes again to remain synced */
        nodes () {
            this.filterByCategory(this.filteredCategories)
        },
    },
    created () {
        this.filteredNodes = this.nodes
        this.setTimelineInstance(this)
        this.syncNodes()
    },
    methods: {
        ...mapMutations({
            setTimelineInstance: 'timeline/SET_TIMELINE_INSTANCE',
            setCurrentNode: 'timeline/SET_CURRENT_NODE',
        }),
        hasCategory (categories, filters) {
            return categories.some((category) => filters.find(
                (filteredCategory) => category.id === filteredCategory.id),
            )
        },
        hasNode (nodes, node) {
            return !!nodes.find((elem) => elem === node || (node && elem.id === node.id))
        },
        /* When a category is linked to or removed from a template, the current list of nodes can become stale.
         * Each of these nodes has been serialized before the category update, and needs to be synced with possible
         * changes. Because these changes can impact the filter, we filter once again afterwards.
         * This only happens during assignment edit, so we can assume the nodes consist of preset nodes.
         *
         * NOTE: called from store
         */
        syncNodes () {
            const templateToCategoriesMap = {}

            /* We can assume the store categories contain the latest state */
            this.$store.getters['category/assignmentCategories'].forEach((category) => {
                category.templates.forEach((template) => {
                    const categoryConcreteFields = {
                        id: category.id,
                        name: category.name,
                        color: category.color,
                        description: category.description,
                    }

                    if (template.id in templateToCategoriesMap) {
                        templateToCategoriesMap[template.id].push(categoryConcreteFields)
                    } else {
                        templateToCategoriesMap[template.id] = [categoryConcreteFields]
                    }
                })
            })

            this.nodes.map((node) => {
                if (node.type === 'd') {
                    node.template.categories = templateToCategoriesMap[node.template.id] || []
                    return node
                }
                return node
            })

            this.filterByCategory(this.filteredCategories)
        },
        /* If a node was selected which is no longer part of the filtered nodes, selects the start of the assignment. */
        filterByCategory (filters) {
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
                    } else if (node.type === 'a' || node.type === 'p') {
                        return true
                    }
                    return false
                })
            }

            if (!this.hasNode(this.filteredNodes, this.currentNode)) {
                this.setCurrentNode(this.startNode)
            }
        },
    },
}
</script>

<style lang="sass">
@import '~sass/partials/shadows.sass'

#timeline-container
    position: relative
    @include lg
        display: block !important

.timeline-filter
    position: static !important
    vertical-align: top
    display: inline
    .dropdown-toggle
        text-decoration: none
        border-width: 0px
        padding: 0px
        .filter-button
            padding: 0.15em 0.6em
            &:hover, &:focus, &:active
                border-color: inherit !important
    .dropdown-menu
        width: 100%
        margin-top: 5px
        padding: 0px
        border: none
        .multiselect--active .multiselect__content-wrapper
            box-shadow: none
            position: relative

#timeline-toggle
    display: none

@include lg-max
    /* Handles changing of the button icon. */
    [aria-expanded="false"] .timeline-container__icon--open
        display: block
        text-align: center

    [aria-expanded="false"] .timeline-container__icon--close
        display: none
        text-align: center

    [aria-expanded="true"] .timeline-container__icon--open
        display: none
        text-align: center

    [aria-expanded="true"] .timeline-container__icon--close
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
