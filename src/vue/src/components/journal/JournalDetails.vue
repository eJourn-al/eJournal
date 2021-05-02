<template>
    <b-card
        class="journal-details-card"
        noBody
    >
        <template #header>
            <h3 class="theme-h3">
                Details
            </h3>
            <b-button
                v-if="canManageJournal"
                variant="link"
                class="float-right grey-button mt-0 mb-0"
                @click="showModal('editJournalModal')"
            >
                <icon name="edit"/>
                Edit
            </b-button>
        </template>
        <b-card-body class="d-flex flex-wrap">
            <img
                :src="journal.image"
                class="journal-image mr-2"
            />
            <div
                v-if="!assignment.is_group_assignment && $hasPermission('can_view_all_journals')"
                class="flex-grow-1"
            >
                <span class="max-one-line">
                    {{ journal.full_names }}
                </span>
                <span class="max-one-line small">
                    {{ journal.usernames }}
                </span>
            </div>
            <progress-bar
                :currentPoints="journal.grade"
                :totalPoints="assignment.points_possible"
                :comparePoints="assignment && assignment.stats ? assignment.stats.average_points : -1"
                :bonusPoints="journal.bonus_points"
                class="flex-grow-1"
                :class="{
                    'flex-basis-100': !assignment.is_group_assignment && $hasPermission('can_view_all_journals'),
                    'mt-2': !assignment.is_group_assignment && $hasPermission('can_view_all_journals'),
                }"
            />
        </b-card-body>
        <journal-members
            v-if="assignment.is_group_assignment"
            :journal="journal"
            :assignment="assignment"
        />
        <edit-journal-modal
            v-if="canManageJournal"
            ref="editJournalModal"
            :journal="journal"
            :assignment="assignment"
            @journal-updated="hideModal('editJournalModal')"
            @journal-deleted="$router.push($root.assignmentRoute(assignment))"
        />
        <slot
            slot="footer"
            name="footer"
        />
    </b-card>
</template>

<script>
import editJournalModal from '@/components/journal/EditJournalModal.vue'
import journalMembers from '@/components/journal/JournalMembers.vue'
import progressBar from '@/components/assets/ProgressBar.vue'

export default {
    components: {
        editJournalModal,
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
        showModal (ref) {
            this.$refs[ref].show()
        },
        hideModal (ref) {
            this.$refs[ref].hide()
        },
    },
}
</script>

<style lang="sass">
.journal-details-card
    .journal-image
        border: 1px solid $border-color
        width: 40px
        height: 40px
        border-radius: 50% !important
        background-color: white
</style>
