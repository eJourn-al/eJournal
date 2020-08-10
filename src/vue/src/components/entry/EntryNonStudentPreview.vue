<!--
    Loads a filled in template of an entry and the corresponding
    comments. The teacher tools will also be loaded if the user has the
    right permissions.
-->
<template>
    <div v-if="entryNode.entry !== null">
        <b-card
            class="no-hover entry-card-teacher"
            :class="$root.getBorderClass($route.params.cID)"
        >
            <div>
                <div
                    v-if="$hasPermission('can_grade')"
                    class="grade-section sticky"
                >
                    <b-form-input
                        v-model="grade.grade"
                        type="number"
                        class="theme-input"
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
                        :selectedOption="this.$store.getters['preferences/gradeButtonSetting']"
                        :options="{
                            s: {
                                text: 'Save grade',
                                icon: 'save',
                                class: 'add-button',
                            },
                            p: {
                                text: 'Save & publish grade',
                                icon: 'save',
                                class: 'add-button',
                            },
                        }"
                        @click="commitGrade"
                        @change-option="changeButtonOption"
                    />
                </div>
                <div
                    v-else-if="gradePublished"
                    class="grade-section grade"
                >
                    {{ entryNode.entry.grade.grade }}
                </div>
                <div
                    v-else
                    class="grade-section grade"
                >
                    <icon name="hourglass-half"/>
                </div>

                <h2 class="theme-h2 mb-2">
                    {{ entryNode.entry.template.name }}
                </h2>
                <entry-fields
                    :nodeID="entryNode.nID"
                    :template="entryNode.entry.template"
                    :completeContent="completeContent"
                    :displayMode="true"
                    :journalID="journal.id"
                    :entryID="entryNode.entry.id"
                />
            </div>
            <hr class="full-width"/>
            <div class="timestamp">
                <span v-if="entryNode.entry.last_edited_by == null">
                    Submitted on: {{ $root.beautifyDate(entryNode.entry.creation_date) }}
                    <template v-if="assignment && assignment.is_group_assignment">
                        by {{ entryNode.entry.author }}
                    </template>
                </span>
                <span v-else>
                    Last edited: {{ $root.beautifyDate(entryNode.entry.last_edited) }}
                    <template v-if="assignment && assignment.is_group_assignment">
                        by {{ entryNode.entry.last_edited_by }}
                    </template>
                </span>
                <b-badge
                    v-if="entryNode.due_date && new Date(entryNode.due_date) < new Date(entryNode.entry.last_edited)"
                    class="late-submission-badge"
                >
                    LATE
                </b-badge>
            </div>
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
            <b-card class="no-hover">
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
                        slot="published"
                        slot-scope="data"
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
                        slot="creation_date"
                        slot-scope="data"
                    >
                        {{ $root.beautifyDate(data.value) }}
                    </template>
                </b-table>
                <div v-else>
                    <h4 class="theme-h4">
                        No grades available
                    </h4>
                    <hr class="m-0 mb-1"/>
                    This entry has not yet been graded.
                </div>
            </b-card>
        </b-modal>
    </div>
    <b-card
        v-else
        :class="$root.getBorderClass($route.params.cID)"
        class="no-hover"
    >
        <h2 class="theme-h2 mb-2">
            {{ entryNode.template.name }}
        </h2>
        <b>No submission for this student</b>
    </b-card>
</template>

<script>
import comments from '@/components/entry/Comments.vue'
import dropdownButton from '@/components/assets/DropdownButton.vue'
import entryFields from '@/components/entry/EntryFields.vue'
import gradeAPI from '@/api/grade.js'
import preferencesAPI from '@/api/preferences.js'

export default {
    components: {
        comments,
        dropdownButton,
        entryFields,
    },
    props: ['entryNode', 'journal', 'assignment'],
    data () {
        return {
            completeContent: [],
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
    },
    watch: {
        entryNode () {
            this.completeContent = []
            this.setContent()

            if (this.entryNode.entry && this.entryNode.entry.grade) {
                this.grade = this.entryNode.entry.grade
            } else {
                this.grade = {
                    grade: '',
                    published: false,
                }
            }
        },
    },
    created () {
        this.setContent()

        if (this.entryNode.entry && this.entryNode.entry.grade) {
            this.grade = this.entryNode.entry.grade
        } else {
            this.grade = {
                grade: '',
                published: false,
            }
        }
    },
    methods: {
        setContent () {
            /* Loads in the data of an entry in the right order by matching
             * the different data-fields with the corresponding template-IDs. */
            let matchFound

            if (this.entryNode.entry) {
                this.entryNode.entry.template.field_set.sort((a, b) => a.location - b.location)
                    .forEach((templateField) => {
                        matchFound = false

                        matchFound = this.entryNode.entry.content.some((content) => {
                            if (content.field === templateField.id) {
                                this.completeContent.push({
                                    data: content.data,
                                    id: content.field,
                                    contentID: content.id,
                                })

                                return true
                            }

                            return false
                        })

                        if (!matchFound) {
                            this.completeContent.push({
                                data: null,
                                id: templateField.id,
                            })
                        }
                    })
            }
        },
        changeButtonOption (option) {
            preferencesAPI.update(this.$store.getters['user/uID'], { grade_button_setting: option })
                .then((preferences) => {
                    this.$store.commit('preferences/SET_GRADE_BUTTON_SETTING',
                        preferences.grade_button_setting)
                })
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
                    .then(() => {
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
