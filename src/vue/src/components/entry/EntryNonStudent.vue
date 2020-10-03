<template>
    <div v-if="entryNode.entry !== null">
        <b-card
            class="no-hover"
            :class="$root.getBorderClass($route.params.cID)"
        >
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
                :content="entryNode.entry.content"
                :edit="false"
            />
            <div class="full-width timestamp">
                <hr class="full-width"/>
                <template
                    v-if="(new Date(entryNode.entry.last_edited).getTime() - new Date(entryNode.entry.creation_date)
                        .getTime()) / 1000 < 3"
                >
                    Submitted:
                </template>
                <template v-else>
                    Last edited:
                </template>
                {{ $root.beautifyDate(entryNode.entry.last_edited) }} by {{ entryNode.entry.last_edited_by }}
                <b-badge
                    v-if="entryNode.due_date && new Date(entryNode.due_date) < new Date(entryNode.entry.last_edited)"
                    v-b-tooltip:hover="'This entry was submitted after the due date'"
                    pill
                    class="late-submission-badge"
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
                <div v-else>
                    <b>No grades available</b>
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
        <span class="text-grey">
            No submission for this student
        </span>
    </b-card>
</template>

<script>
import comments from '@/components/entry/Comments.vue'
import dropdownButton from '@/components/assets/DropdownButton.vue'
import entryFields from '@/components/entry/EntryFields.vue'
import gradeAPI from '@/api/grade.js'

export default {
    components: {
        comments,
        dropdownButton,
        entryFields,
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
    },
    watch: {
        entryNode () {
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
        changeButtonOption (option) {
            this.$store.commit('preferences/CHANGE_PREFERENCES', { grade_button_setting: option })
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
