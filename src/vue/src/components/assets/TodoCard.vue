<template>
    <b-card :class="$root.getBorderClass(deadline.id)">
        <!-- Teacher show things todo -->
        <number-badge
            v-if="thingsToDo"
            :absolute="false"
            :badges="badges"
            :displayZeroValues="false"
            class="float-right multi-form"
            keyPrefix="todo"
        />

        <b class="field-heading align-top">
            <!-- {{ deadline.name }} -->
            Logboek Academia
        </b>
        <span class="align-middle">
            {{ courseAbbreviations }}
        </span>
        <b-badge
            v-if="!deadline.is_published"
            v-b-tooltip:hover="'This assignment is not yet published'"
            pill
            class="background-medium-grey text-grey align-middle"
        >
            <icon name="eye-slash"/>
        </b-badge>
        <br/>
        <!-- Teacher deadline shows last submitted entry date  -->
        <span v-if="$hasPermission('can_view_all_journals', 'assignment', deadline.id)">
            <span v-if="thingsToDo">
                <icon
                    name="eye"
                    class="fill-grey shift-up-3"
                /> {{ timeLeft[1] }} ago<br/>
                <icon
                    name="flag"
                    class="fill-grey shift-up-3"
                /> {{ $root.beautifyDate(deadline.deadline.date) }}
            </span>
        </span>
        <span v-else-if="deadline.deadline.date">
            <!-- Student deadline shows last not submitted deadline -->
            <icon
                name="calendar"
                class="fill-grey shift-up-3 mr-1"
            />
            <span v-if="timeLeft[0] < 0">Due in {{ timeLeft[1] }}<br/></span>
            <span
                v-else
                class="text-red"
            >{{ timeLeft[1] }} late<br/></span>
            <icon
                name="flag"
                class="fill-grey shift-up-3"
            /> {{ deadline.deadline.name }}
        </span>
    </b-card>
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
                const abbrList = this.courses.map(c => c.abbreviation)
                return `(${abbrList.join(', ')})`
            } else {
                return `(${this.deadline.course.abbreviation})`
            }
        },
        timeLeft () {
            if (!this.deadline.deadline.date) { return '' }
            const dateNow = new Date()
            const dateFuture = new Date(this.deadline.deadline.date)

            // get total seconds between the times
            let delta = Math.abs(dateFuture - dateNow) / 1000
            const dir = dateNow - dateFuture

            // calculate (and subtract) whole days
            const days = Math.floor(delta / 86400)
            delta -= days * 86400

            // calculate (and subtract) whole hours
            const hours = Math.floor(delta / 3600) % 24
            delta -= hours * 3600

            // calculate (and subtract) whole minutes
            const minutes = Math.floor(delta / 60) % 60
            delta -= minutes * 60

            if (days) {
                return [dir, days > 1 ? `${days} days` : '1 day']
            }

            if (hours) {
                return [dir, hours > 1 ? `${hours} hours` : '1 hour']
            }

            return [dir, minutes > 1 ? `${minutes} minutes` : '1 minute']
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
