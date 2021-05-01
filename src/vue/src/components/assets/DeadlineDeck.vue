<template>
    <b-card
        slot="right-content-column"
        class="todo-deck"
    >
        <template slot="header">
            <h3
                class="theme-h3 d-inline"
            >
                To do
            </h3>
            <div
                v-if="$root.canGradeForSomeCourse()"
                class="text-grey small float-right unselectable cursor-pointer"
            >
                <span
                    v-if="filterOwnGroups"
                    v-b-tooltip.hover
                    title="Only showing to do items for groups of which you are a member"
                    @click="filterOwnGroups = false"
                >
                    Showing:
                    <b>own groups</b>
                </span>
                <span
                    v-else
                    v-b-tooltip.hover
                    title="Showing to do items for all groups"
                    @click="filterOwnGroups = true"
                >
                    Showing:
                    <b>all groups</b>
                </span>
            </div>
        </template>
        <load-wrapper :loading="loadingDeadlines">
            <b-list-group
                v-if="computedDeadlines.length > 0"
                flush
                class="todo-list-group"
            >
                <b-list-group-item
                    v-if="$root.canGradeForSomeCourse() && computedDeadlines.length > 1"
                    class="todo-teacher-filter"
                >
                    <b-form-select
                        v-model="sortBy"
                        :selectSize="1"
                        class="theme-select"
                    >
                        <option value="date">
                            Sort by date
                        </option>
                        <option value="markingNeeded">
                            Sort by marking needed
                        </option>
                    </b-form-select>
                </b-list-group-item>
                <b-list-group-item
                    v-for="(d, i) in computedDeadlines"
                    :key="i"
                >
                    <b-link :to="$root.assignmentRoute(d)">
                        <todo-item
                            :deadline="d"
                            :courses="d.courses"
                            :filterOwnGroups="filterOwnGroups"
                        />
                    </b-link>
                </b-list-group-item>
            </b-list-group>
            <div
                v-else
                class="mb-2"
            >
                <icon
                    name="check"
                    class="fill-green shift-up-4"
                />
                <b>
                    All done!
                </b><br/>
                <span class="small">
                    You do not have any {{ $root.canGradeForSomeCourse()
                        ? `entries to grade${filterOwnGroups ? ' (in your own groups)' : ''}`
                        : 'upcoming deadlines' }}
                    at this moment.
                </span>
            </div>
        </load-wrapper>
    </b-card>
</template>

<script>
import assignmentAPI from '@/api/assignment.js'
import comparison from '@/utils/comparison.js'

import { mapGetters, mapMutations } from 'vuex'
import loadWrapper from '@/components/loading/LoadWrapper.vue'
import todoItem from '@/components/assets/TodoItem.vue'

export default {
    components: {
        todoItem,
        loadWrapper,
    },
    data () {
        return {
            deadlines: [],
            loadingDeadlines: true,
        }
    },
    computed: {
        ...mapGetters({
            getSortBy: 'preferences/todoSortBy',
            getFilterOwnGroups: 'preferences/todoFilterOwnGroups',
        }),
        sortBy: {
            get () {
                return this.getSortBy
            },
            set (value) {
                this.setSortBy(value)
            },
        },
        filterOwnGroups: {
            get () {
                return this.getFilterOwnGroups
            },
            set (value) {
                this.setFilterOwnGroups(value)
            },
        },
        computedDeadlines () {
            let deadlines = this.deadlines
            if (this.$root.canGradeForSomeCourse() && deadlines.length > 0) {
                if (this.filterOwnGroups) {
                    deadlines = deadlines.filter(
                        (dd) => (
                            dd.stats.needs_marking_own_groups
                            + dd.stats.unpublished_own_groups
                            + dd.stats.import_requests_own_groups
                        ) > 0
                        || !dd.is_published,
                    )
                } else {
                    deadlines = deadlines.filter(
                        (d) => (
                            d.stats.needs_marking
                            + d.stats.unpublished
                            + d.stats.import_requests
                        ) > 0
                        || !d.is_published,
                    )
                }
            } else {
                deadlines = deadlines.filter(
                    (d) => d.deadline.date !== null)
            }

            if (this.sortBy === 'date') {
                deadlines.sort(comparison.date)
            } else if (this.sortBy === 'markingNeeded') {
                deadlines.sort(this.filterOwnGroups ? comparison.markingNeededOwnGroups : comparison.markingNeededAll)
            }

            return deadlines
        },
    },
    created () {
        /* Providing a cID to upcoming will only yield upcoming for that specific course,
         * If we are on the home page, we want all ToDos of an assignment (for all of its courses) */
        assignmentAPI.getUpcoming(this.$route.params.cID)
            .then((deadlines) => {
                this.deadlines = deadlines
                this.loadingDeadlines = false
            })
    },
    methods: {
        ...mapMutations({
            setSortBy: 'preferences/SET_TODO_SORT_BY',
            setFilterOwnGroups: 'preferences/SET_TODO_FILTER_OWN_GROUPS',
        }),
    },
}
</script>

<style lang="sass">
.card.todo-deck
    .card-body
        border-radius: 0px 0px 5px 5px
        overflow: hidden
        padding-bottom: 0px
    .todo-list-group
        margin: -10px -10px 0px -10px
        .list-group-item
            padding: 10px
            &:not(.todo-teacher-filter):hover
                transition: all 0.3s cubic-bezier(.25,.8,.25,1) !important
                background-color: $theme-light-grey
            &:nth-of-type(even)
                background-color: lighten($theme-light-grey, 3%)
            &:last-child
                border-bottom-left-radius: 10px
                border-bottom-right-radius: 10px
</style>
