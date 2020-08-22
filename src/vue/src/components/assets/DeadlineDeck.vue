<template>
    <div>
        <h3
            slot="right-content-column"
            class="theme-h3"
        >
            To Do
        </h3>
        <div
            v-if="$root.canGradeForSomeCourse()"
            class="text-grey float-right unselectable cursor-pointer"
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
        <load-wrapper :loading="loadingDeadlines">
            <div v-if="computedDeadlines.length > 0">
                <b-form-select
                    v-if="$root.canGradeForSomeCourse() && computedDeadlines.length > 1"
                    v-model="sortBy"
                    :selectSize="1"
                    class="theme-select multi-form"
                >
                    <option value="date">
                        Sort by date
                    </option>
                    <option value="markingNeeded">
                        Sort by marking needed
                    </option>
                </b-form-select>
                <div
                    v-for="(d, i) in computedDeadlines"
                    :key="i"
                >
                    <b-link
                        :to="$root.assignmentRoute(d)"
                        tag="b-button"
                    >
                        <todo-card
                            :deadline="d"
                            :course="d.course"
                            :filterOwnGroups="filterOwnGroups"
                        />
                    </b-link>
                </div>
            </div>
            <b-card
                v-else
                class="border-dark-grey no-hover"
            >
                <div class="text-center multi-form">
                    <icon
                        name="check"
                        scale="4"
                        class="fill-green mb-2 text-shadow"
                    /><br/>
                    <b class="field-heading">
                        All done!
                    </b>
                </div>
                You do not have any {{ $root.canGradeForSomeCourse()
                    ? `entries to grade${filterOwnGroups ? ' (in your own groups)' : ''}`
                    : 'upcoming deadlines' }}
                at this moment.
            </b-card>
        </load-wrapper>
    </div>
</template>

<script>
import assignmentAPI from '@/api/assignment.js'

import todoCard from '@/components/assets/TodoCard.vue'
import loadWrapper from '@/components/loading/LoadWrapper.vue'
import { mapGetters, mapMutations } from 'vuex'

export default {
    components: {
        todoCard,
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
            function compareDate (a, b) {
                if (!a.deadline.date) { return 1 }
                if (!b.deadline.date) { return -1 }
                return new Date(a.deadline.date) - new Date(b.deadline.date)
            }

            const filterOwnGroupsCopy = this.filterOwnGroups
            function compareMarkingNeeded (a, b) {
                if (filterOwnGroupsCopy) {
                    return (
                        b.stats.needs_marking_own_groups
                        + b.stats.unpublished_own_groups
                        + b.stats.import_requests_own_groups
                    ) - (
                        a.stats.needs_marking_own_groups
                        + a.stats.unpublished_own_groups
                        + a.stats.import_requests_own_groups
                    )
                } else {
                    return (b.stats.needs_marking + b.stats.unpublished + b.stats.import_requests)
                        - (a.stats.needs_marking + a.stats.unpublished + a.stats.import_requests)
                }
            }

            let deadlines = this.deadlines
            if (this.$root.canGradeForSomeCourse() && deadlines.length > 0) {
                if (this.filterOwnGroups) {
                    deadlines = deadlines.filter(
                        dd => (dd.stats.needs_marking_own_groups + dd.stats.unpublished_own_groups) > 0
                        || !dd.is_published,
                    )
                } else {
                    deadlines = deadlines.filter(
                        d => d.stats.needs_marking + d.stats.unpublished > 0 || !d.is_published,
                    )
                }
            } else {
                deadlines = deadlines.filter(
                    d => d.deadline.date !== null)
            }

            if (this.sortBy === 'date') {
                deadlines.sort(compareDate)
            } else if (this.sortBy === 'markingNeeded') {
                deadlines.sort(compareMarkingNeeded)
            }

            return deadlines
        },
    },
    created () {
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
