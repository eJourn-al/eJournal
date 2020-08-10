<template>
    <b-card
        :class="$root.getBorderClass(journal.id)"
        class="journal-card"
    >
        <b-row noGutters>
            <b-col
                class="d-flex"
                :md="$hasPermission('can_view_all_journals') ? 7 : 12"
            >
                <div class="portrait-wrapper">
                    <img
                        class="no-hover"
                        :src="journal.image"
                    />
                    <number-badge
                        v-if="$hasPermission('can_view_all_journals') &&
                            journal.needs_marking + journal.unpublished > 0"
                        :leftNum="journal.needs_marking"
                        :rightNum="journal.unpublished"
                        :title="squareInfo"
                    />
                </div>
                <div class="student-details">
                    <b
                        class="max-one-line"
                        :title="journal.name"
                    >
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
                            class="text-white mr-1"
                        >
                            {{ journal.author_count }}/{{ journal.author_limit }}
                        </b-badge>
                        <b-badge
                            v-if="journal.author_limit === 0"
                            v-b-tooltip:hover="`This journal currently has ${ journal.author_count } members `
                                + 'and no member limit'"
                            class="text-white mr-1"
                        >
                            {{ journal.author_count }}
                        </b-badge>
                        <b-badge
                            v-if="journal.locked"
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
                        <span v-if="!assignment.is_group_assignment || !expanded">
                            {{ journal.usernames }}
                        </span>
                    </span>
                </div>
            </b-col>
            <b-col
                v-if="$hasPermission('can_view_all_journals')"
                class="mt-2"
                md="5"
            >
                <progress-bar
                    :currentPoints="journal.grade"
                    :totalPoints="assignment.points_possible"
                />
            </b-col>
        </b-row>
        <slot/>
        <div
            v-if="assignment.is_group_assignment && $hasPermission('can_manage_journals')"
            class="expand-controls full-width text-center"
            @click.prevent.stop="expanded = !expanded"
        >
            <icon
                :name="expanded ? 'caret-up' : 'caret-down'"
                class="fill-grey"
            />
        </div>
        <div
            v-if="expanded"
            class="mt-3 mb-4"
            @click.prevent.stop=""
        >
            <journal-members
                v-if="assignment.is_group_assignment"
                :journal="journal"
                :assignment="assignment"
            />
        </div>
    </b-card>
</template>

<script>
import progressBar from '@/components/assets/ProgressBar.vue'
import numberBadge from '@/components/assets/NumberBadge.vue'
import journalMembers from '@/components/journal/JournalMembers.vue'

export default {
    components: {
        progressBar,
        numberBadge,
        journalMembers,
    },
    props: {
        assignment: {
            required: true,
        },
        journal: {
            required: true,
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
        squareInfo () {
            const info = []
            if (this.journal.needs_marking === 1) {
                info.push('an entry needs marking')
            } else if (this.journal.needs_marking > 1) {
                info.push(`${this.journal.needs_marking} entries need marking`)
            }
            if (this.journal.unpublished === 1) {
                info.push('a grade needs to be published')
            } else if (this.journal.unpublished > 1) {
                info.push(`${this.journal.unpublished} grades need to be published`)
            }
            const s = info.join(' and ')
            return `${s.charAt(0).toUpperCase()}${s.slice(1)}`
        },
        canManageJournal () {
            return this.assignment.is_group_assignment && (this.assignment.can_set_journal_name
                || this.assignment.can_set_journal_image || this.$hasPermission('can_manage_journals'))
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
@import '~sass/partials/shadows.sass'
@import '~sass/modules/breakpoints.sass'
@import '~sass/modules/colors.sass'

.journal-card
    .portrait-wrapper
        position: relative
        min-width: 80px
        height: 70px
        img
            @extend .theme-shadow
            width: 70px
            height: 70px
            border-radius: 50% !important
        .number-badge
            position: absolute
            right: 0px
            top: 0px
    .student-details
        position: relative
        width: calc(100% - 80px)
        min-height: 70px
        flex-direction: column
        padding: 10px
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
