<template>
    <div>
        <!-- Teacher show things todo -->
        <number-badge
            v-if="thingsToDo"
            :absolute="false"
            :badges="badges"
            :displayZeroValues="false"
            class="float-right ml-2 mb-2"
            keyPrefix="todo"
        />
        <b-badge
            v-if="!deadline.is_published"
            v-b-tooltip:hover="'This assignment is not yet published'"
            pill
            class="background-medium-grey text-grey align-middle float-right mb-2"
        >
            <icon
                name="eye-slash"
                scale="0.8"
            />
        </b-badge>

        {{ deadline.name }}
        <span class="small">
            {{ courseAbbreviations }}
        </span>
        <br/>
        <!-- Teacher deadline shows last submitted entry date  -->
        <span
            v-if="$hasPermission('can_view_all_journals', 'assignment', deadline.id)"
            class="small"
        >
            <span v-if="thingsToDo">
                <icon
                    name="edit"
                    class="fill-grey shift-up-2"
                    scale="0.8"
                /> <timeago :datetime="deadline.deadline.date"/>
            </span>
        </span>
        <span
            v-else-if="deadline.deadline.date"
            class="small"
        >
            <!-- Student deadline shows last not submitted deadline -->
            <icon
                name="calendar"
                class="fill-grey shift-up-3 mr-1"
                scale="0.8"
            />
            {{ deadline.deadline.name }}
            <span v-if="new Date() < new Date(deadline.deadline.date)">
                due in <timeago :datetime="deadline.deadline.date"/>
            </span>
            <span
                v-else
                class="text-red"
            >
                due <timeago :datetime="deadline.deadline.date"/>
            </span>
        </span>
    </div>
</template>

<script>
import NumberBadge from '@/components/assets/NumberBadge.vue'

export default {
    components: {
        NumberBadge,
    },
    props: {
        deadline: {
            required: true,
        },
        courses: {
            required: true,
        },
        filterOwnGroups: {
            required: false,
            default: false,
        },
    },
    computed: {
        badges () {
            const badges = [
                {
                    value: this.filterOwnGroups ? this.deadline.stats.needs_marking_own_groups
                        : this.deadline.stats.needs_marking,
                    tooltip: 'needsMarking',
                },
                {
                    value: this.filterOwnGroups ? this.deadline.stats.unpublished_own_groups
                        : this.deadline.stats.unpublished,
                    tooltip: 'unpublished',
                },
            ]

            if (this.deadline.stats.import_requests) {
                badges.push({
                    value: this.filterOwnGroups ? this.deadline.stats.import_requests_own_groups
                        : this.deadline.stats.import_requests,
                    tooltip: 'importRequests',
                })
            }

            return badges
        },
        courseAbbreviations () {
            if (this.courses) {
                const abbrList = this.courses.map((c) => c.abbreviation)
                return `(${abbrList.join(', ')})`
            } else {
                return `(${this.deadline.course.abbreviation})`
            }
        },
        squareInfo () {
            const info = []
            const needsMarking = this.filterOwnGroups ? this.deadline.stats.needs_marking_own_groups
                : this.deadline.stats.needs_marking
            const unpublished = this.filterOwnGroups ? this.deadline.stats.unpublished_own_groups
                : this.deadline.stats.unpublished

            if (needsMarking === 1) {
                info.push('an entry needs marking')
            } else if (needsMarking > 1) {
                info.push(`${needsMarking} entries need marking`)
            }
            if (unpublished === 1) {
                info.push('a grade needs to be published')
            } else if (unpublished > 1) {
                info.push(`${unpublished} grades need to be published`)
            }
            const s = info.join(' and ')
            return `${s.charAt(0).toUpperCase()}${s.slice(1)}`
        },
        thingsToDo () {
            if (this.filterOwnGroups) {
                return this.deadline.stats
                    && (this.deadline.stats.needs_marking_own_groups || this.deadline.stats.unpublished_own_groups
                        || this.deadline.stats.import_requests_own_groups)
            } else {
                return this.deadline.stats
                    && (this.deadline.stats.needs_marking || this.deadline.stats.unpublished
                        || this.deadline.stats.import_requests)
            }
        },
    },
}
</script>
