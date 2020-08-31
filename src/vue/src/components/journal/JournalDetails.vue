<template>
    <div
        class="journal-details"
        :class="$root.getBorderClass($route.params.cID)"
    >
        <img
            :src="journal.image"
            class="journal-image no-hover"
        />
        <span
            v-if="canManageJournal"
            class="edit-journal"
            @click="showEditJournalModal"
        >
            <icon name="edit"/>
            Edit
        </span>
        <span
            v-if="!assignment.is_group_assignment"
            class="journal-name mt-2"
        >
            {{ journal.name }}
        </span>
        <progress-bar
            :currentPoints="journal.grade"
            :totalPoints="assignment.points_possible"
            :comparePoints="assignment && assignment.stats ? assignment.stats.average_points : -1"
            :bonusPoints="journal.bonus_points"
        />
        <journal-members
            v-if="assignment.is_group_assignment"
            :journal="journal"
            :assignment="assignment"
            class="mt-2"
        />
        <b-modal
            v-if="canManageJournal"
            ref="editJournalModal"
            size="lg"
            title="Edit journal"
            hideFooter
        >
            <edit-journal
                :journal="journal"
                :assignment="assignment"
                @journal-updated="hideEditJournalModal"
                @journal-deleted="$router.push($root.assignmentRoute(assignment))"
            />
        </b-modal>
    </div>
</template>

<script>
import editJournal from '@/components/journal/EditJournal.vue'
import journalMembers from '@/components/journal/JournalMembers.vue'
import progressBar from '@/components/assets/ProgressBar.vue'

export default {
    components: {
        editJournal,
        progressBar,
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
    computed: {
        canManageJournal () {
            return this.assignment.is_group_assignment && (this.assignment.can_set_journal_name
                || this.assignment.can_set_journal_image || this.$hasPermission('can_grade'))
        },
    },
    methods: {
        showEditJournalModal () {
            this.$refs.editJournalModal.show()
        },
        hideEditJournalModal () {
            this.$refs.editJournalModal.hide()
        },
    },
}
</script>

<style lang="sass">
@import '~sass/partials/shadows.sass'
@import '~sass/modules/breakpoints.sass'
@import '~sass/modules/colors.sass'

.journal-details
    .journal-image
        @extend .theme-shadow
        position: absolute
        width: 70px
        height: 70px
        left: 50%
        top: -25px
        margin-left: -35px
        border-radius: 50% !important
        background-color: white
    .journal-name
        text-align: center
        display: block
        font-weight: bold
    .edit-journal
        position: absolute
        right: 10px
        top: 5px
        color: grey
        svg
            margin-top: -2px
            fill: grey !important
        &:hover:not(.no-hover)
            cursor: pointer
            color: darken(grey, 20)
            svg
                fill: darken(grey, 20) !important
</style>
