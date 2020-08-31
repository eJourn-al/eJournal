<template>
    <div>
        <div
            v-if="teacherEntries && teacherEntries.length > 0"
            class="d-flex"
        >
            <theme-select
                v-model="selectedTeacherEntry"
                label="title"
                trackBy="id"
                :options="teacherEntries"
                :multiple="false"
                :searchable="true"
                placeholder="Select A Teacher Entry"
                class="flex-shrink-1"
            />
            <b-button
                v-if=" selectedTeacherEntry && showTeacherEntryContent"
                class="delete-button ml-2"
                @click="showTeacherEntryContent = false"
            >
                <icon name="eye-slash"/>
            </b-button>
            <b-button
                v-else-if="selectedTeacherEntry"
                class="add-button ml-2"
                @click="showTeacherEntryContent = true"
            >
                <icon name="eye"/>
            </b-button>
        </div>
        <span
            v-else
            class="mb-2"
        >
            No teacher entries for this assignment. Once you have posted a teacher entry you can manage it here.
        </span>
        <div v-if="selectedTeacherEntry">
            <entry-fields
                v-if="showTeacherEntryContent"
                :template="selectedTeacherEntry.template"
                :content="selectedTeacherEntry.content"
                :edit="false"
                class="mt-3"
            />
            <hr/>
            <h2 class="theme-h2 field-heading">
                Journals to add
            </h2>
            <theme-select
                v-model="selectedJournals"
                label="name"
                trackBy="id"
                :options="assignmentJournals"
                :multiple="true"
                :searchable="true"
                placeholder="Select Journals"
            />
            <small v-if="!showUsernameInput">
                Or
                <span
                    class="text-blue cursor-pointer"
                    @click="showUsernameInput = true"
                >
                    select by username</span>.
                <br/>
            </small>
            <b-input
                v-else
                v-model="usernameInput"
                class="theme-input mt-2"
                placeholder="Enter a username and press enter to select"
                @keydown.enter.native="selectUsername"
            />
            <b-table-simple
                v-if="selectedTeacherEntry && selectedJournals.length > 0"
                responsive
                striped
                noSortReset
                sortBy="name"
                class="mt-2 mb-0"
            >
                <b-thead>
                    <b-tr>
                        <b-th>
                            Name
                        </b-th>
                        <b-th>
                            Username
                        </b-th>
                        <b-th>
                            Grade
                        </b-th>
                        <b-th>
                            Published
                            <tooltip tip="Make the grade visible to students"/>
                        </b-th>
                    </b-tr>
                </b-thead>
                <b-tbody>
                    <b-tr
                        v-for="journal in selectedJournals"
                        :key="journal.id"
                    >
                        <b-td>
                            {{ journal.name }}
                        </b-td>
                        <b-td>
                            {{ journal.usernames }}
                        </b-td>
                        <b-td>
                            <b-form-input
                                v-model="grades[journal.id]"
                                type="number"
                                min="0"
                                placeholder="-"
                                class="theme-input teacher-entry-grade"
                                size="3"
                            />
                        </b-td>
                        <b-td>
                            <b-form-checkbox v-model="publishGrade[journal.id]"/>
                        </b-td>
                        <b-td>
                            <icon
                                name="trash"
                                class="trash-icon"
                                @click.native="selectedJournals.pop(journal)"
                            />
                        </b-td>
                    </b-tr>
                </b-tbody>
            </b-table-simple>

            <b-button
                class="delete-button float-left clearfix mr-2 mt-2"
                :class="{ 'input-disabled': requestInFlight }"
                @click="deleteTeacherEntry"
            >
                <icon name="trash"/>
                Delete
            </b-button>
            <b-button
                class="add-button float-right clearfix ml-2 mt-2"
                :class="{ 'input-disabled': requestInFlight }"
                @click="saveTeacherEntry"
            >
                <icon name="save"/>
                Save
            </b-button>
        </div>
    </div>
</template>

<script>
import EntryFields from '@/components/entry/EntryFields.vue'
import Tooltip from '@/components/assets/Tooltip.vue'

import assignmentAPI from '@/api/assignment.js'
import teacherEntryAPI from '@/api/teacherEntry.js'

export default {
    components: {
        EntryFields,
        Tooltip,
    },
    props: {
        aID: {
            required: true,
        },
        assignmentJournals: {
            required: true,
        },
    },
    data () {
        return {
            selectedJournals: [],
            showUsernameInput: false,
            usernameInput: null,
            requestInFlight: false,
            teacherEntries: [],
            selectedTeacherEntry: null,
            showTeacherEntryContent: false,
            grades: Object(),
            publishGrade: Object(),
        }
    },
    computed: {
        selectedJournalIDs () {
            return this.selectedJournals.map(journal => journal.id)
        },
    },
    watch: {
        selectedTeacherEntry: {
            handler () {
                this.showTeacherEntryContent = false
                if (this.selectedTeacherEntry) {
                    this.selectedJournals = this.assignmentJournals.filter(
                        journal => this.selectedTeacherEntry.journal_ids.includes(journal.id))
                    this.grades = Object.assign({}, this.selectedTeacherEntry.grades)
                    this.publishGrade = Object.assign({}, this.selectedTeacherEntry.grade_published)
                }
            },
            immediate: true,
        },
    },
    created () {
        assignmentAPI.getTeacherEntries(this.aID).then((entries) => {
            this.teacherEntries = entries
        })
    },
    methods: {
        selectUsername () {
            // Split input on comma and space
            this.usernameInput.split(/[ ,]+/).forEach((username) => {
                const journalFromUsername = this.assignmentJournals.find(journal => journal.usernames.split(', ')
                    .some(journalUsername => journalUsername === username))

                if (!journalFromUsername) {
                    this.$toasted.error(`${username} does not exist!`)
                } else if (!this.selectedJournals.includes(journalFromUsername)) {
                    this.selectedJournals.push(journalFromUsername)
                }
            })

            this.usernameInput = null
        },
        saveTeacherEntry () {
            if (this.selectedJournals.length === 0) {
                this.$toasted.error('No journals selected.')
            } else if (this.selectedJournals.some(journal => this.selectedTeacherEntry.grades[journal.id]
                && !this.grades[journal.id])) {
                this.$toasted.error('It is not possible to remove grades from entries that have previously been '
                    + 'graded. Ensure a grade is provided for each of these.')
            } else if (this.selectedJournals.some(journal => !this.grades[journal.id])
                && !window.confirm('Students will be able to edit the entry if no grade is set. Are you sure you'
                + ' want to post ungraded entries?')) {
                this.$toasted.error('Changes not saved: no grade set.')
            } else if (this.selectedTeacherEntry.journal_ids.some(
                journalID => !this.selectedJournalIDs.includes(journalID)) && !window.confirm('The entry will be '
                    + 'deleted from journals that have been unselected. Are you sure you want to proceed? This action '
                    + 'is irreversible!')) {
                this.$toasted.error('Canceled updating the entry.')
            } else {
                this.requestInFlight = true
                teacherEntryAPI.update(this.selectedTeacherEntry.id, {
                    journal_ids: this.selectedJournalIDs,
                    grades: this.grades,
                    publish_grade: this.publishGrade,
                }, { customSuccessToast: 'Teacher entry successfully updated.' })
                    .then((data) => {
                        this.requestInFlight = false
                        this.$emit('teacher-entry-updated', data)
                    })
                    .catch(() => { this.requestInFlight = false })
            }
        },
        deleteTeacherEntry () {
            if (window.confirm('Are you sure you want to delete this teacher entry? This will also remove it from any '
                + 'journals it is in and cannot be undone!')) {
                this.requestInFlight = true
                teacherEntryAPI.delete(this.selectedTeacherEntry.id,
                    { customSuccessToast: 'Teacher entry successfully updated.' })
                    .then((data) => {
                        this.requestInFlight = false
                        this.$emit('teacher-entry-updated', data)
                    })
                    .catch(() => { this.requestInFlight = false })
            }
        },
    },
}
</script>

<style lang="sass">
.teacher-entry-grade
    width: 4em
    display: inline-block
</style>
