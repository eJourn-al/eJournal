<template>
    <div>
        <template v-if="templates && templates.length > 0">
            <h2 class="theme-h2 field-heading required">
                Title
            </h2>
            <b-input
                v-model="title"
                placeholder="Enter A Title"
                type="text"
                class="theme-input"
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
                @select="teacherEntryContent = Object()"
            />
        </template>
        <span
            v-else
            class="mb-2"
        >
            No templates for this assignment. Create some in the assignment editor first.
        </span>
        <div v-if="selectedTemplate">
            <entry-fields
                :template="selectedTemplate"
                :content="teacherEntryContent"
                :edit="true"
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
            <b-form-checkbox
                v-model="sameGradeForAllEntries"
                class="mt-2 mr-2 d-inline-block"
                @change="selectedJournals.forEach((journal) => {
                    if (!grades[journal.id] || (grade && grades[journal.id] !== grade)) {
                        grades[journal.id] = grade
                    }
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
                    class="theme-input mt-2 teacher-entry-grade"
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
                class="add-button float-right ml-2 mt-2"
                :class="{ 'input-disabled': requestInFlight }"
                @click="createTeacherEntry"
            >
                <icon name="paper-plane"/>
                Post
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
            selectedTemplate: null,
            templates: null,
            showUsernameInput: false,
            usernameInput: null,
            sameGradeForAllEntries: true,
            grade: null,
            publishSameGrade: true,
            grades: Object(),
            publishGrade: Object(),
            teacherEntryContent: Object(),
            requestInFlight: false,
            title: null,
            showTitleInTimeline: true,
        }
    },
    created () {
        assignmentAPI.getTemplates(this.aID)
            .then((templates) => {
                this.templates = templates
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
        createTeacherEntry () {
            if (this.selectedTemplate.field_set.some(
                field => field.required && !this.teacherEntryContent[field.id])) {
                this.$toasted.error('Some required fields are empty.')
            } else if (this.selectedJournals.length === 0) {
                this.$toasted.error('No journals selected.')
            } else if (((this.sameGradeForAllEntries && !this.grade)
                || (!this.sameGradeForAllEntries && this.selectedJournals.some(journal => !this.grades[journal.id])))
                && !window.confirm('Students will be able to edit the entry if no grade is set. Are you sure you'
                + ' want to post ungraded entries?')) {
                this.$toasted.error('Teacher entry not posted: no grade set.')
            } else {
                this.requestInFlight = true
                teacherEntryAPI.create({
                    title: this.title,
                    show_title_in_timeline: this.showTitleInTimeline,
                    assignment_id: this.$route.params.aID,
                    template_id: this.selectedTemplate.id,
                    content: this.teacherEntryContent,
                    journal_ids: this.selectedJournals.map(journal => journal.id),
                    // If the same grade shall be used for each entry, create an object containing that grade for each
                    // selected journal. The API always expects a dict for the grades.
                    grades: this.sameGradeForAllEntries
                        ? this.selectedJournals.reduce((gradeObject, journal) => Object.assign(gradeObject, {
                            [journal.id]: this.grade,
                        }), {})
                        : this.grades,
                    publish_grade: this.sameGradeForAllEntries
                        ? this.selectedJournals.reduce((publishObject, journal) => Object.assign(publishObject, {
                            [journal.id]: this.publishSameGrade,
                        }), {})
                        : this.publishGrade,
                }, { customSuccessToast: 'Teacher entry successfully posted.' })
                    .then((data) => {
                        this.requestInFlight = false
                        this.$emit('teacher-entry-posted', data)
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
