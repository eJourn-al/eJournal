<template>
    <b-modal
        ref="postTeacherEntry"
        title="Post teacher entries"
        size="lg"
        noEnforceFocus
    >
        <template v-if="templates && templates.length > 0">
            <h2 class="theme-h2 field-heading required">
                Title
            </h2>
            <b-input
                v-model="title"
                placeholder="Enter A Title"
                type="text"
            />
            <b-form-checkbox
                v-model="showTitleInTimeline"
                class="mt-2 mr-2 d-inline-block"
            >
                Show title in timeline
            </b-form-checkbox>
            <tooltip tip="Show this title instead of the template name in the timeline: keep it short for readability"/>
            <theme-select
                v-model="selectedTemplate"
                label="name"
                trackBy="id"
                :options="templates"
                :multiple="false"
                :searchable="true"
                placeholder="Select A Template"
                class="mt-2"
                @select="
                    teacherEntryContent = Object()
                    teacherEntryCategories = { categories: (selectedTemplate) ? selectedTemplate.categories : [] }
                "
            />
        </template>
        <span
            v-else
            class="mb-2"
        >
            No templates for this assignment. Create some in the assignment editor first.
        </span>
        <template v-if="selectedTemplate">
            <entry-fields
                :template="selectedTemplate"
                :content="teacherEntryContent"
                :edit="true"
                class="mt-3"
            />

            <entry-categories
                :id="`teacher-entry-create-template-${selectedTemplate.id}`"
                :create="true"
                :entry="teacherEntryCategories"
                :template="selectedTemplate"
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
                @select="newJournal"
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
            <template v-else>
                <b-input
                    v-model="usernameInput"
                    class="mt-2"
                    placeholder="Enter a username and press enter to select"
                    @keydown.enter.native="selectUsername"
                />
                <small>
                    <b>Tip:</b>
                    you can also copy a spreadsheet column and paste it in the input above.
                    <br/>
                </small>
            </template>
            <b-form-checkbox
                v-model="sameGradeForAllEntries"
                class="mt-2 mr-2 d-inline-block"
                @change="selectedJournals.forEach((journal) => {
                    journal.grade = grade
                    journal.published = publishSameGrade
                })"
            >
                Use same grade for all entries<span v-if="sameGradeForAllEntries">:</span>
            </b-form-checkbox>
            <template v-if="sameGradeForAllEntries">
                <b-form-input
                    v-model="grade"
                    type="number"
                    min="0"
                    placeholder="-"
                    class="inline mt-2"
                    size="3"
                />
                <b-form-checkbox
                    v-if="sameGradeForAllEntries"
                    v-model="publishSameGrade"
                >
                    Publish grades
                    <tooltip tip="Make the grade visible to students"/>
                </b-form-checkbox>
            </template>
            <b-table-simple
                v-else-if="selectedJournals.length > 0"
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
                        <b-th/>
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
                                class="inline"
                                size="3"
                            />
                        </b-td>
                        <b-td class="align-middle">
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
        </template>
        <template #modal-footer>
            <b-button
                class="green-button float-right"
                :class="{ 'input-disabled': requestInFlight || !selectedTemplate }"
                @click="createTeacherEntry"
            >
                <icon name="paper-plane"/>
                Post
            </b-button>
        </template>
    </b-modal>
</template>

<script>
import EntryCategories from '@/components/category/EntryCategories.vue'
import EntryFields from '@/components/entry/EntryFields.vue'
import Tooltip from '@/components/assets/Tooltip.vue'

import teacherEntryAPI from '@/api/teacherEntry.js'

import { mapGetters } from 'vuex'

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
            selectedTemplate: null,
            showUsernameInput: false,
            usernameInput: null,
            sameGradeForAllEntries: true,
            grade: null,
            publishSameGrade: true,
            teacherEntryContent: Object(),
            teacherEntryCategories: {},
            requestInFlight: false,
            title: null,
            showTitleInTimeline: true,
        }
    },
    computed: {
        ...mapGetters({
            templates: 'template/assignmentTemplates',
        }),
        selectableJournals () {
            const journalList = []
            this.assignmentJournals.forEach((journal) => {
                journalList.push({
                    journal_id: journal.id,
                    grade: this.grade,
                    published: this.publishSameGrade,
                    name: journal.name,
                    usernames: journal.usernames,
                })
            })

            return journalList
        },
    },
    methods: {
        selectUsername () {
            // Split input on comma and space
            this.usernameInput.split(/[ ,]+/).forEach((username) => {
                const journalFromUsername = this.assignmentJournals.find((journal) => journal.usernames.split(', ')
                    .some((journalUsername) => journalUsername === username))

                if (!journalFromUsername) {
                    this.$toasted.error(`${username} does not exist.`)
                } else if (!this.selectedJournals.some((journal) => journal.journal_id === journalFromUsername.id)) {
                    this.selectedJournals.push({
                        journal_id: journalFromUsername.id,
                        grade: this.grade,
                        published: this.publishSameGrade,
                        name: journalFromUsername.name,
                        usernames: journalFromUsername.usernames,
                    })
                }
            })

            this.usernameInput = null
        },
        createTeacherEntry () {
            if (this.selectedTemplate.field_set.some(
                (field) => field.required && !this.teacherEntryContent[field.id])) {
                this.$toasted.error('Some required fields are empty.')
            } else if (this.selectedJournals.length === 0) {
                this.$toasted.error('No journals selected.')
            } else if (((this.sameGradeForAllEntries && !this.grade)
                || (!this.sameGradeForAllEntries && this.selectedJournals.some((journal) => !journal.grade)))
                && !window.confirm('Students will be able to edit the entry if no grade is set. Are you sure you'
                + ' want to post ungraded entries?')) {
                this.$toasted.error('Teacher entry not posted: no grade set.')
            } else {
                this.requestInFlight = true
                if (this.sameGradeForAllEntries) {
                    this.selectedJournals.forEach((journal) => {
                        journal.grade = this.grade
                        journal.published = this.publishSameGrade
                    })
                }
                teacherEntryAPI.create({
                    title: this.title,
                    show_title_in_timeline: this.showTitleInTimeline,
                    assignment_id: this.$route.params.aID,
                    template_id: this.selectedTemplate.id,
                    content: this.teacherEntryContent,
                    category_ids: this.teacherEntryCategories.categories.map((category) => category.id),
                    journals: this.selectedJournals,
                }, {
                    customSuccessToast: 'Teacher entry successfully posted.',
                })
                    .then((data) => {
                        this.$emit('teacher-entry-posted', data)
                        this.selectedJournals = []
                        this.selectedTemplate = null
                        this.showUsernameInput = false
                        this.usernameInput = null
                        this.sameGradeForAllEntries = true
                        this.grade = null
                        this.publishSameGrade = true
                        this.teacherEntryContent = Object()
                        this.teacherEntryCategories = {}
                        this.requestInFlight = false
                        this.title = null
                        this.showTitleInTimeline = true
                    })
                    .catch(() => { this.requestInFlight = false })
            }
        },
        newJournal (journal) {
            journal.grade = this.grade
            journal.published = this.publishSameGrade
        },
        show () {
            this.$refs.postTeacherEntry.show()
        },
        hide () {
            this.$refs.postTeacherEntry.hide()
        },
    },
}
</script>
