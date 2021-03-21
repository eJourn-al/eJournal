<template>
    <div>
        <div
            v-if="teacherEntries && teacherEntries.length > 0"
            class="d-lg-flex"
        >
            <theme-select
                v-model="selectedTeacherEntry"
                label="title"
                trackBy="id"
                :options="teacherEntries"
                :multiple="false"
                :searchable="true"
                placeholder="Select A Teacher Entry"
                class="flex-shrink-1 mb-2 mr-md-2"
            />
            <b-button
                v-if="selectedTeacherEntry"
                class="orange-button mr-2 flex-shrink-0 mb-2"
                @click="toggleUpdateTitle"
            >
                <icon name="edit"/>
                Edit title
            </b-button>
            <b-button
                v-if="selectedTeacherEntry && showTeacherEntryContent"
                class="red-button flex-shrink-0 mb-2"
                @click="showTeacherEntryContent = false"
            >
                <icon name="eye-slash"/>
                Hide Content
            </b-button>
            <b-button
                v-else-if="selectedTeacherEntry"
                class="green-button flex-shrink-0 mb-2"
                @click="showTeacherEntryContent = true"
            >
                <icon name="eye"/>
                Show&nbsp;Content
            </b-button>
        </div>
        <span
            v-else
            class="mb-2"
        >
            No teacher entries for this assignment. Once you have posted a teacher entry you can manage it here.
        </span>
        <div v-if="selectedTeacherEntry">
            <b-input
                v-if="showUpdateTitle"
                v-model="updatedTitle"
                placeholder="New title"
                class="theme-input mt-2"
            />
            <entry-fields
                v-if="showTeacherEntryContent"
                :template="selectedTeacherEntry.template"
                :content="selectedTeacherEntry.content"
                :edit="false"
                class="mt-3"
            />

            <entry-categories
                :id="`edit-teacher-entry-${selectedTeacherEntry.id}`"
                :entry="selectedTeacherEntry"
                :template="selectedTeacherEntry.template"
                :edit="true"
                :autosave="false"
            />

            <hr/>
            <h2 class="theme-h2 field-heading">
                Journals to add
            </h2>
            <theme-select
                v-model="selectedJournals"
                label="name"
                trackBy="journal_id"
                :options="selectableJournals"
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
                        v-for="(journal, i) in selectedJournals"
                        :key="journal.journal_id"
                    >
                        <b-td class="align-middle">
                            {{ journal.name }}
                        </b-td>
                        <b-td class="align-middle">
                            {{ journal.usernames }}
                        </b-td>
                        <b-td class="align-middle">
                            <b-form-input
                                v-model="journal.grade"
                                type="number"
                                min="0"
                                placeholder="-"
                                class="theme-input inline"
                                size="3"
                            />
                        </b-td>
                        <b-td>
                            <b-form-checkbox v-model="journal.published"/>
                        </b-td>
                        <b-td class="align-middle">
                            <icon
                                name="trash"
                                class="trash-icon"
                                @click.native="selectedJournals.splice(i, 1)"
                            />
                        </b-td>
                    </b-tr>
                </b-tbody>
            </b-table-simple>

            <b-button
                class="red-button float-left clearfix mr-2 mt-2"
                :class="{ 'input-disabled': requestInFlight }"
                @click="deleteTeacherEntry"
            >
                <icon name="trash"/>
                Delete
            </b-button>
            <b-button
                class="green-button float-right clearfix ml-2 mt-2"
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
import EntryCategories from '@/components/category/EntryCategories.vue'
import EntryFields from '@/components/entry/EntryFields.vue'
import Tooltip from '@/components/assets/Tooltip.vue'

import assignmentAPI from '@/api/assignment.js'
import teacherEntryAPI from '@/api/teacherEntry.js'

export default {
    components: {
        EntryFields,
        Tooltip,
        EntryCategories,
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
            selectableJournals: [],
            showUsernameInput: false,
            usernameInput: null,
            requestInFlight: false,
            teacherEntries: [],
            selectedTeacherEntry: null,
            showTeacherEntryContent: false,
            grades: Object(),
            publishGrade: Object(),
            showUpdateTitle: false,
            updatedTitle: null,
            updatedCategories: null,
        }
    },
    computed: {
        hasRemovedJournal () {
            const journalIds = this.selectedJournals.map((journal) => journal.id)
            return this.selectedTeacherEntry.journals.some((journal) => !journalIds.includes(journal.id))
        },
    },
    watch: {
        selectedTeacherEntry: {
            handler () {
                this.showTeacherEntryContent = false
                if (this.selectedTeacherEntry) {
                    this.updatedTitle = this.selectedTeacherEntry.title
                    this.showUpdateTitle = false
                    this.selectedJournals = this.selectedTeacherEntry.journals
                }
            },
            immediate: true,
        },
    },
    created () {
        assignmentAPI.getTeacherEntries(this.aID).then((entries) => {
            this.teacherEntries = entries
        })
        this.assignmentJournals.forEach((journal) => {
            this.selectableJournals.push({
                journal_id: journal.id,
                grade: this.grade,
                published: this.publishSameGrade,
                name: journal.name,
                usernames: journal.usernames,
            })
        })
    },
    methods: {
        selectUsername () {
            // Split input on comma and space
            this.usernameInput.split(/[ ,]+/).forEach((username) => {
                const journalFromUsername = this.assignmentJournals.find((journal) => journal.usernames.split(', ')
                    .some((journalUsername) => journalUsername === username))

                if (!journalFromUsername) {
                    this.$toasted.error(`${username} does not exist`)
                } else if (!this.selectedJournals.includes(journalFromUsername)) {
                    this.selectedJournals.push({
                        journal_id: journalFromUsername.id,
                        grade: null,
                        published: false,
                        name: journalFromUsername.name,
                        usernames: journalFromUsername.usernames,
                    })
                }
            })

            this.usernameInput = null
        },
        saveTeacherEntry () {
            if (this.selectedJournals.length === 0) {
                this.$toasted.error('No journals selected.')
            } else if (!this.updatedTitle) {
                this.$toasted.error('Title cannot be empty.')
            } else if (this.selectedJournals.some((journal) => !journal.grade)
                && !window.confirm('Students will be able to edit the entry if no grade is set. Are you sure you'
                + ' want to post ungraded entries?')) {
                this.$toasted.error('Changes not saved: no grade set.')
            } else if (this.hasRemovedJournal && !window.confirm('The entry will be '
                    + 'deleted from journals that have been unselected. Are you sure you want to proceed? This action '
                    + 'is irreversible!')) {
                this.$toasted.error('Canceled updating the entry.')
            } else {
                this.requestInFlight = true
                teacherEntryAPI.update(this.selectedTeacherEntry.id, {
                    journals: this.selectedJournals,
                    title: this.updatedTitle,
                    category_ids: this.selectedTeacherEntry.categories.map((elem) => elem.id),
                }, {
                    customSuccessToast: 'Teacher entry successfully updated.',
                })
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
                    { customSuccessToast: 'Teacher entry successfully deleted.' })
                    .then((data) => {
                        this.requestInFlight = false
                        this.$emit('teacher-entry-updated', data)
                    })
                    .catch(() => { this.requestInFlight = false })
            }
        },
        toggleUpdateTitle () {
            if (this.showUpdateTitle && this.selectedTeacherEntry) {
                this.updatedTitle = this.selectedTeacherEntry.title
            }
            this.showUpdateTitle = !this.showUpdateTitle
        },
    },
}
</script>
