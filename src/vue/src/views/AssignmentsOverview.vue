<template>
    <content-single-column>
        <div
            v-if="$root.canGradeForSomeCourse"
            class="text-grey float-right unselectable cursor-pointer"
        >
            <span
                v-if="filterOwnGroups"
                v-b-tooltip.hover
                title="Only showing to do items for groups of which you are a member"
                @click="filterOwnGroups = false"
            >
                Showing to do:
                <b>own groups</b>
            </span>
            <span
                v-else
                v-b-tooltip.hover
                title="Showing to do items for all groups"
                @click="filterOwnGroups = true"
            >
                Showing to do:
                <b>all</b>
            </span>
        </div>

        <bread-crumb/>

        <input
            v-model="searchValue"
            class="theme-input full-width multi-form"
            type="text"
            placeholder="Search..."
        />

        <div class="d-flex">
            <b-form-select
                v-model="sortBy"
                :selectSize="1"
                class="theme-select multi-form mr-2"
            >
                <option value="date">
                    Sort by date
                </option>
                <option value="name">
                    Sort by name
                </option>
                <option
                    v-if="$root.canGradeForSomeCourse"
                    value="markingNeeded"
                >
                    Sort by marking needed
                </option>
            </b-form-select>
            <b-button
                v-if="!order"
                class="button multi-form"
                @click.stop
                @click="setOrder(!order)"
            >
                <icon name="long-arrow-alt-down"/>
                Ascending
            </b-button>
            <b-button
                v-if="order"
                class="button multi-form"
                @click.stop
                @click="setOrder(!order)"
            >
                <icon name="long-arrow-alt-up"/>
                Descending
            </b-button>
        </div>

        <load-wrapper :loading="loadingAssignments">
            <div
                v-for="(d, i) in computedAssignments"
                :key="i"
            >
                <b-link
                    :to="$root.assignmentRoute(d)"
                    tag="b-button"
                >
                    <todo-card
                        :deadline="d"
                        :courses="d.courses"
                        :filterOwnGroups="filterOwnGroups"
                    />
                </b-link>
            </div>
            <main-card
                v-if="computedAssignments.length === 0"
                text="No assignments found"
                class="no-hover"
            >
                You currently do not participate in any assignments.
            </main-card>
        </load-wrapper>
    </content-single-column>
</template>

<script>
import contentSingleColumn from '@/components/columns/ContentSingleColumn.vue'
import breadCrumb from '@/components/assets/BreadCrumb.vue'
import loadWrapper from '@/components/loading/LoadWrapper.vue'
import todoCard from '@/components/assets/TodoCard.vue'
import mainCard from '@/components/assets/MainCard.vue'
import assignmentAPI from '@/api/assignment.js'
import comparison from '@/utils/comparison.js'

import { mapGetters, mapMutations } from 'vuex'

export default {
    name: 'AssignmentsOverview',
    components: {
        contentSingleColumn,
        breadCrumb,
        loadWrapper,
        todoCard,
        mainCard,
    },
    data () {
        return {
            assignments: [],
            loadingAssignments: true,
        }
    },
    computed: {
        ...mapGetters({
            order: 'preferences/assignmentOverviewSortAscending',
            getAssignmentSearchValue: 'preferences/assignmentOverviewSearchValue',
            getAssignmentOverviewSortBy: 'preferences/assignmentOverviewSortBy',
            getAssignmentOverviewFilterOwnGroups: 'preferences/assignmentOverviewFilterOwnGroups',
        }),
        searchValue: {
            get () {
                return this.getAssignmentSearchValue
            },
            set (value) {
                this.setAssignmentSearchValue(value)
            },
        },
        sortBy: {
            get () {
                return this.getAssignmentOverviewSortBy
            },
            set (value) {
                this.setAssignmentOverviewSortBy(value)
            },
        },
        filterOwnGroups: {
            get () {
                return this.getAssignmentOverviewFilterOwnGroups
            },
            set (value) {
                this.setAssignmentOverviewOwnGroups(value)
            },
        },
        computedAssignments () {
            const self = this

            function compareName (a, b) {
                return b.name < a.name
            }

            function searchFilter (assignment) {
                return assignment.name.toLowerCase().includes(self.getAssignmentSearchValue.toLowerCase())
            }

            const deadlines = this.assignments.filter(searchFilter)
            if (this.sortBy === 'name') {
                deadlines.sort(compareName)
            } else if (this.sortBy === 'date') {
                deadlines.sort(comparison.date)
            } else if (this.sortBy === 'markingNeeded') {
                deadlines.sort(this.filterOwnGroups ? comparison.markingNeededOwnGroups : comparison.markingNeededAll)
            }

            return this.order ? deadlines.reverse() : deadlines
        },
    },
    created () {
        assignmentAPI.list()
            .then((assignments) => {
                this.assignments = assignments
                this.loadingAssignments = false
            })
    },
    methods: {
        ...mapMutations({
            setOrder: 'preferences/SET_ASSIGNMENT_OVERVIEW_SORT_ASCENDING',
            setAssignmentSearchValue: 'preferences/SET_ASSIGNMENT_OVERVIEW_SEARCH_VALUE',
            setAssignmentOverviewSortBy: 'preferences/SET_ASSIGNMENT_OVERVIEW_SORT_BY',
            setAssignmentOverviewOwnGroups: 'preferences/SET_ASSIGNMENT_OVERVIEW_FILTER_OWN_GROUPS',
        }),
    },
}
</script>
