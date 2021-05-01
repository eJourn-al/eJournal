<template>
    <b-modal
        ref="editJournalModal"
        size="lg"
        title="Edit journal"
    >
        <div v-if="assignment.can_set_journal_image || $hasPermission('can_manage_journals')">
            <h2 class="theme-h2 field-heading mb-2">
                Image
            </h2>
            <cropper
                ref="journalImageCropper"
                class="mb-2"
                :pictureUrl="newJournalImage"
                :hideSaveButton="true"
            />
        </div>
        <div v-if="assignment.can_set_journal_name || $hasPermission('can_manage_journals')">
            <h2 class="theme-h2 field-heading mb-2 required">
                Name
            </h2>
            <b-input
                v-model="newJournalName"
                placeholder="Journal name"
                class="mb-2"
                required
            />
        </div>
        <div v-if="assignment.is_group_assignment && $hasPermission('can_manage_journals')">
            <h2 class="theme-h2 field-heading">
                Member limit
            </h2>
            <b-input
                v-model="newJournalMemberLimit"
                type="number"
                placeholder="No member limit"
                min="2"
                class="mb-2"
            />
        </div>
        <template #modal-footer>
            <b-button
                v-if="assignment.is_group_assignment && $hasPermission('can_manage_journals')"
                :class="{
                    'input-disabled': journal.author_count > 0,
                }"
                class="red-button mr-auto"
                @click="deleteJournal"
            >
                <icon name="trash"/>
                Delete journal
            </b-button>
            <b-button
                class="green-button"
                @click="updateJournal"
            >
                <icon name="save"/>
                Save
            </b-button>
        </template>
    </b-modal>
</template>

<script>
import cropper from '@/components/assets/ImageCropper.vue'

import journalAPI from '@/api/journal.js'

export default {
    name: 'EditJournal',
    components: {
        cropper,
    },
    props: {
        journal: {
            required: true,
        },
        assignment: {
            required: true,
        },
    },
    data () {
        return {
            newJournalImage: null,
            newJournalName: '',
            newJournalMemberLimit: null,
            saveRequestInFlight: false,
        }
    },
    created () {
        this.newJournalImage = this.journal.image
        this.newJournalName = this.journal.name
        if (this.journal.author_limit > 1) {
            this.newJournalMemberLimit = this.journal.author_limit
        }
    },
    methods: {
        updateJournal () {
            const newJournalData = {}
            if (this.assignment.can_set_journal_image || this.$hasPermission('can_manage_journals')) {
                this.newJournalImage = this.$refs.journalImageCropper.getPicture()
                if (this.newJournalImage !== this.journal.image) {
                    newJournalData.image = this.newJournalImage
                }
            }
            if (this.newJournalName !== this.journal.name) {
                if (!this.newJournalName) {
                    this.$toasted.error('A journal must have a valid name.')
                    return
                }
                newJournalData.name = this.newJournalName
            }
            if (this.assignment.is_group_assignment && this.$hasPermission('can_manage_journals')
                && this.newJournalMemberLimit !== this.journal.author_limit) {
                if (this.newJournalMemberLimit > 0) {
                    if (this.newJournalMemberLimit < this.journal.author_count) {
                        this.$toasted.error('It is not possible to set a member limit lower than the number of '
                        + 'journal members.')
                        return
                    }
                    newJournalData.author_limit = this.newJournalMemberLimit
                } else if (this.journal.author_limit > 1) {
                    newJournalData.author_limit = 0
                }
            }

            this.saveRequestInFlight = true
            journalAPI.update(this.journal.id, newJournalData,
                { customSuccessToast: 'Successfully updated journal' })
                .then((journal) => {
                    this.journal.name = journal.name
                    this.journal.image = journal.image
                    this.journal.author_limit = journal.author_limit
                    this.saveRequestInFlight = false
                    this.$emit('journal-updated')
                })
                .catch(() => { this.saveRequestInFlight = false })
        },
        deleteJournal () {
            this.saveRequestInFlight = true
            if (window.confirm('Are you sure you want to delete this journal?')) {
                journalAPI.delete(this.journal.id, { responseSuccessToast: true })
                    .then(() => {
                        this.saveRequestInFlight = false
                        this.$emit('journal-deleted')
                    })
                    .catch(() => { this.saveRequestInFlight = false })
            } else {
                this.saveRequestInFlight = false
            }
        },
        show () {
            this.$refs.editJournalModal.show()
        },
        hide () {
            this.$refs.editJournalModal.hide()
        },
    },
}
</script>
