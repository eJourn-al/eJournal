<template>
    <div v-if="entryNode.entry !== null">
        <b-card class="sticky-header">
            <template slot="header">
                <div
                    v-if="$hasPermission('can_grade')"
                    class="grade-section"
                >
                    <b-input-group>
                        <template
                            v-if="usingDefaultGrade && defaultGrade === grade.grade"
                            #prepend
                        >
                            <b-input-group-text
                                v-b-tooltip="'Default grade: not saved'"
                                class="text-white"
                            >
                                <icon name="exclamation"/>
                            </b-input-group-text>
                        </template>
                    </b-input-group>
                    <b-form-input
                        v-model="grade.grade"
                        type="number"
                        size="2"
                        autofocus
                        placeholder="0"
                        min="0.0"
                    />
                    <b-button
                        v-if="$hasPermission('can_view_grade_history')"
                        class="grade-history-button float-right"
                        @click="showGradeHistory"
                    >
                        <icon name="history"/>
                    </b-button>
                    <dropdown-button
                        :selectedOption="this.$store.getters['preferences/saved'].grade_button_setting"
                        :options="{
                            s: {
                                text: 'Save grade',
                                icon: 'save',
                                class: 'green-button',
                            },
                            p: {
                                text: 'Save & publish grade',
                                icon: 'save',
                                class: 'green-button',
                            },
                        }"
                        @click="commitGrade"
                        @change-option="changeButtonOption"
                    />
                </div>
                <span
                    v-if="!$hasPermission('can_grade') && gradePublished"
                    class="float-right"
                >
                    Grade: <b>{{ entryNode.entry.grade.grade }}</b>
                </span>
                <span
                    v-else-if="!$hasPermission('can_grade')"
                    class="float-right"
                >
                    Grade:
                    <icon
                        v-b-tooltip.hover="'Awaiting grade.'"
                        name="hourglass-half"
                        class="shift-up-2"
                    />
                </span>

                <h2 class="theme-h2">
                    {{ entryNode.entry.template.name }}
                </h2>
                <small>
                    Posted
                    <timeago
                        v-b-tooltip.hover="$root.beautifyDate(entryNode.entry.creation_date)"
                        :datetime="entryNode.entry.creation_date"
                    />
                    by {{ entryNode.entry.author }}
                    <icon
                        v-if="(new Date(entryNode.entry.last_edited).getTime() - new Date(entryNode.entry.creation_date)
                            .getTime()) / 1000 > 180"
                        v-b-tooltip.hover="`Last edited ${$root.beautifyDate(entryNode.entry.last_edited)} by
                            ${entryNode.entry.last_edited_by}`"
                        class="ml-1 fill-grey"
                        scale="0.8"
                        name="history"
                    />
                    <br/>
                    <b-badge
                        v-if="entryNode.due_date && new Date(entryNode.due_date) <
                            new Date(entryNode.entry.last_edited)"
                        v-b-tooltip:hover="'This entry was posted after the due date'"
                        pill
                        class="late-submission-badge mr-2"
                    >
                        LATE
                    </b-badge>
                    <b-badge
                        v-if="entryNode.entry.jir"
                        v-b-tooltip:hover="
                            `This entry has been imported from the assignment
                            ${entryNode.entry.jir.source.assignment.name}
                            (${entryNode.entry.jir.source.assignment.course.abbreviation}), approved by
                            ${entryNode.entry.jir.processor.full_name}`"
                        pill
                        class="imported-entry-badge"
                    >
                        IMPORTED
                    </b-badge>
                </small>
            </template>

            <entry-fields
                :nodeID="entryNode.id"
                :template="entryNode.entry.template"
                :content="entryNode.entry.content"
                :edit="false"
            />
            <entry-categories
                :id="`entry-${entryNode.entry.id}-entry-categories`"
                :entry="entryNode.entry"
                :template="entryNode.entry.template"
                class="align-top mr-2 mt-2"
            />
            <deadline-date-display
                v-if="entryNode.type === 'd'"
                class="d-inline-block mt-2 align-top"
                :subject="entryNode"
            />
        </b-card>

        <comments
            :eID="entryNode.entry.id"
            :entryGradePublished="gradePublished"
            @publish-grade="commitGrade('p')"
        />

        <b-modal
            id="gradeHistoryModal"
            ref="gradeHistoryModal"
            size="lg"
            title="Grade history"
            hideFooter
            noEnforceFocus
        >
            <b-table
                v-if="gradeHistory.length > 0"
                responsive
                striped
                noSortReset
                sortBy="date"
                :sortDesc="true"
                :items="gradeHistory"
                class="mb-0"
            >
                <template
                    v-slot:cell(published)="data"
                >
                    <icon
                        v-if="data.value"
                        name="check"
                        class="fill-green"
                    />
                    <icon
                        v-else
                        name="times"
                        class="fill-red"
                    />
                </template>
                <template
                    v-slot:cell(creation_date)="data"
                >
                    {{ $root.beautifyDate(data.value) }}
                </template>
            </b-table>
            <not-found
                v-else
                subject="grades"
                explanation="This entry has not yet been graded."
            />
        </b-modal>
    </div>
    <b-card v-else>
        <template slot="header">
            <entry-title
                :template="entryNode.template"
                :node="entryNode"
            />
        </template>
        <i class="text-grey">
            No submission<br/>
        </i>
        <entry-categories
            :id="`entry-${entryNode.id}-preview-entry-categories`"
            :entry="{}"
            :displayOnly="true"
            :template="entryNode.template"
            class="align-top mt-2 mr-2"
        />
        <deadline-date-display
            v-if="entryNode.type === 'd'"
            class="mt-2 align-top"
            :subject="entryNode"
        />
    </b-card>
</template>

<script>
import DeadlineDateDisplay from '@/components/assets/DeadlineDateDisplay.vue'
import EntryCategories from '@/components/category/EntryCategories.vue'
import EntryTitle from '@/components/entry/EntryTitle.vue'
import comments from '@/components/entry/Comments.vue'
import dropdownButton from '@/components/assets/DropdownButton.vue'
import entryFields from '@/components/entry/EntryFields.vue'
import gradeAPI from '@/api/grade.js'

export default {
    components: {
        comments,
        dropdownButton,
        entryFields,
        EntryCategories,
        EntryTitle,
        DeadlineDateDisplay,
    },
    props: ['entryNode', 'journal', 'assignment'],
    data () {
        return {
            gradeHistory: [],
            grade: {
                grade: '',
                published: false,
            },
        }
    },
    computed: {
        gradePublished () {
            return this.entryNode.entry && this.entryNode.entry.grade && this.entryNode.entry.grade.published
        },
        defaultGrade () {
            if (this.entryNode.entry && this.entryNode.entry.template.default_grade !== null) {
                return this.entryNode.entry.template.default_grade
            } else {
                return null
            }
        },
        usingDefaultGrade () {
            return this.defaultGrade && !this.entryNode.entry.grade
        },
    },
    watch: {
        entryNode: 'setGrade',
    },
    created () {
        this.setGrade()
    },
    methods: {
        changeButtonOption (option) {
            this.$store.commit('preferences/CHANGE_PREFERENCES', { grade_button_setting: option })
        },
        setGrade () {
            /* Work with a local grade object, so the entryNode.grade is our original */
            if (this.entryNode.entry && this.entryNode.entry.grade) {
                this.grade.grade = this.entryNode.entry.grade.grade
                this.grade.published = this.entryNode.entry.grade.published
            } else if (this.usingDefaultGrade) {
                this.grade = {
                    grade: this.defaultGrade,
                    published: false,
                }
            } else {
                this.grade = {
                    grade: '',
                    published: false,
                }
            }
        },
        commitGrade (option) {
            if (this.grade.grade !== '') {
                const customSuccessToast = option === 'p' ? 'Grade updated and published.'
                    : 'Grade updated but not published.'
                gradeAPI.grade(
                    {
                        entry_id: this.entryNode.entry.id,
                        grade: this.grade.grade,
                        published: option === 'p',
                    },
                    { customSuccessToast },
                )
                    .then((entry) => {
                        this.grade = entry.grade
                        this.entryNode.entry.grade = entry.grade
                        this.$emit('check-grade')
                    })
            } else {
                this.$toasted.error('Grade field is empty.')
            }
        },
        showGradeHistory () {
            gradeAPI.get_history(
                { entry_id: this.entryNode.entry.id },
            )
                .then((gradeHistory) => { this.gradeHistory = gradeHistory })
            this.$refs.gradeHistoryModal.show()
        },
    },
}
</script>
