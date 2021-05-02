<template>
    <b-card
        class="journal-card"
        :class="{ 'hover': isLink }"
        noBody
    >
        <!-- Link can be disabled for e.g. join journal page. -->
        <b-link
            :is="!isLink ? 'span' : 'b-link'"
            :to="{
                name: 'Journal',
                params: {
                    cID: (assignment.course && assignment.course.id) ? assignment.course.id : $route.params.cID,
                    aID: assignment.id,
                    jID: journal.id
                }
            }"
            :target="openInNewTab ? '_blank' : '_self'"
        >
            <b-card-body>
                <b-row noGutters>
                    <b-col
                        class="d-flex"
                        :md="$hasPermission('can_view_all_journals') ? 7 : 12"
                    >
                        <div class="portrait-wrapper">
                            <img :src="journal.image"/>
                            <number-badge
                                v-if="$hasPermission('can_view_all_journals')
                                    && (journal.needs_marking || journal.unpublished || journal.import_requests)"
                                :badges="badges"
                                :displayZeroValues="false"
                                :keyPrefix="journal.id"
                            />
                        </div>
                        <div class="student-details">
                            <b
                                class="max-one-line"
                                :title="journal.name"
                            >
                                <slot class="float-right"/>
                                {{ journal.name }}
                            </b>
                            <span
                                class="max-one-line shift-up-4"
                                :title="journal.name"
                            >
                                <b-badge
                                    v-if="journal.author_limit > 1"
                                    v-b-tooltip:hover="`This journal currently has ${ journal.author_count } of max `
                                        + `${ journal.author_limit } members`"
                                    pill
                                    class="background-medium-grey text-grey mr-1"
                                >
                                    {{ journal.author_count }}/{{ journal.author_limit }}
                                </b-badge>
                                <b-badge
                                    v-if="journal.author_limit === 0"
                                    v-b-tooltip:hover="`This journal currently has ${ journal.author_count } members `
                                        + 'and no member limit'"
                                    pill
                                    class="background-medium-grey text-grey mr-1"
                                >
                                    {{ journal.author_count }}
                                </b-badge>
                                <b-badge
                                    v-if="journal.locked"
                                    pill
                                    class="background-red"
                                >
                                    <icon
                                        v-b-tooltip:hover="
                                            'Members are locked: it is not possible to join or leave this journal'"
                                        name="lock"
                                        class="fill-white"
                                        scale="0.65"
                                    />
                                </b-badge>
                                <span v-if="assignment.is_group_assignment && !expanded">
                                    {{ journal.full_names }}
                                </span>
                                <span v-else-if="!assignment.is_group_assignment">
                                    {{ journal.usernames }}
                                </span>
                            </span>
                        </div>
                    </b-col>
                    <b-col
                        v-if="$hasPermission('can_view_all_journals')"
                        md="5"
                    >
                        <progress-bar
                            :currentPoints="journal.grade"
                            :totalPoints="assignment.points_possible"
                        />
                    </b-col>
                </b-row>
            </b-card-body>
        </b-link>
        <div
            v-if="assignment.is_group_assignment"
            slot="footer"
            class="expand-controls full-width text-center cursor-pointer"
            @click.prevent.stop="expanded = !expanded"
        >
            <icon
                :name="expanded ? 'caret-up' : 'caret-down'"
                class="fill-grey"
            />
        </div>
        <journal-members
            v-if="expanded"
            :journal="journal"
            :assignment="assignment"
            @click.stop
        />
    </b-card>
</template>

<script>
import NumberBadge from '@/components/assets/NumberBadge.vue'
import journalMembers from '@/components/journal/JournalMembers.vue'
import progressBar from '@/components/assets/ProgressBar.vue'

export default {
    components: {
        progressBar,
        journalMembers,
        NumberBadge,
    },
    props: {
        assignment: {
            required: true,
        },
        journal: {
            required: true,
        },
        isLink: {
            default: true,
        },
        openInNewTab: {
            default: false,
        },
    },
    data () {
        return {
            expanded: false,
        }
    },
    computed: {
        groups () {
            return this.journal.groups.join(', ')
        },
        canManageJournal () {
            return this.assignment.is_group_assignment && (this.assignment.can_set_journal_name
                || this.assignment.can_set_journal_image || this.$hasPermission('can_manage_journals'))
        },
        badges () {
            const badges = [
                { value: this.journal.needs_marking, tooltip: 'needsMarking' },
                { value: this.journal.unpublished, tooltip: 'unpublished' },
            ]

            if (this.$hasPermission('can_manage_journal_import_requests')) {
                badges.push({ value: this.journal.import_requests, tooltip: 'importRequests' })
            }

            return badges
        },
    },
    methods: {
        journalDeleted () {
            this.$emit('journal-deleted')
        },
    },
}
</script>

<style lang="sass">
.journal-card
    .portrait-wrapper
        position: relative
        min-width: 60px
        height: 45px
        img
            border: 1px solid $border-color
            width: 45px
            height: 45px
            border-radius: 50% !important
    .student-details
        position: relative
        width: calc(100% - 60px)
        min-height: 45px
        flex-direction: column
        padding-left: 20px
        .max-one-line
            display: block
            width: 100%
            text-overflow: ellipsis
            white-space: nowrap
            overflow: hidden
        &.list-view
            padding-left: 40px
        @include sm-max
            align-items: flex-end
    .default-cursor
        cursor: default
    .expand-controls
        position: absolute
        bottom: 0px
        left: 0px
</style>
