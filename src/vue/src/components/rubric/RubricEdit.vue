<template>
    <b-card>
        <template #header>
            <template v-if="readMode">
                <b-button
                    class="grey-button float-right ml-2"
                    @click="setModeToEdit()"
                >
                    <icon name="edit"/>
                    Edit
                </b-button>
                <b-button
                    v-if="!create"
                    class="red-button float-right"
                    @click.stop="confirmDeleteRubric()"
                >
                    <icon name="trash"/>
                    Delete
                </b-button>
            </template>
            <b-button
                v-else
                class="float-right ml-2"
                :class="(create) ? 'green-button' : 'red-button'"
                @click="(create) ? setModeToRead() : cancelRubricEdit({ rubric })"
            >
                <icon :name="(create) ? 'eye' : 'ban'"/>
                {{ (create) ? 'Preview' : 'Cancel' }}
            </b-button>
            <h2 class="theme-h2">
                {{ (rubric.name) ? rubric.name : 'Rubric' }}
            </h2>
        </template>

        <rubric-read-mode
            v-if="readMode"
            :rubric="rubric"
        />
        <b-form
            v-else
            id="rubricEditForm"
            @submit.prevent="finalizeRubricChanges"
        >
            <div style="overflow-x:auto;">
                <table class="rubric-edit">
                    <thead>
                        <tr>
                            <th :colspan="3">
                                <!-- {{ rubric.name }} -->
                                <b-form-group
                                    style="max-width: 200px"
                                    :invalid-feedback="nameInvalidFeedback"
                                    :state="nameInputState"
                                >
                                    <b-form-input
                                        v-model="rubric.name"
                                        placeholder="Name"
                                        type="text"
                                        trim
                                        required
                                    />
                                </b-form-group>
                            </th>
                        </tr>

                        <tr class="main-column-headers">
                            <th>Criteria</th>
                            <th>Levels</th>
                            <th>Score</th>
                        </tr>
                    </thead>

                    <tbody>
                        <tr
                            v-for="criterion in rubric.criteria"
                            :key="`criterion-${criterion.id}-row`"
                        >
                            <td class="criterion-cell">
                                <criterion-edit
                                    :rubric="rubric"
                                    :criterion="criterion"
                                />
                            </td>

                            <td class="levels-cell-table-container">
                                <table
                                    class="levels"
                                    style="height: 100%"
                                >
                                    <tbody>
                                        <tr>
                                            <td
                                                v-for="level in criterion.levels"
                                                :key="`criterion-${criterion.id}-level-${level.id}`"
                                            >
                                                <level-edit
                                                    :level="level"
                                                    :criterion="criterion"
                                                />
                                            </td>
                                        </tr>
                                    </tbody>
                                </table>
                            </td>

                            <td class="align-bottom">
                                <span class="oneline">
                                    Max: {{ Math.max(...criterion.levels.map((level) => level.points)) }}
                                </span>
                            </td>
                        </tr>
                    </tbody>

                    <tfoot>
                        <tr>
                            <td colspan="2">
                                <b-button
                                    class="green-button full-width"
                                    @click="addCriterion"
                                >
                                    <icon name="plus"/>
                                    Add criterion
                                </b-button>
                            </td>
                            <td
                                :colspan="criteriaMaxLevelLength"
                                class="text-right"
                            >
                                <span class="oneline">Sum: {{ pointSum }}</span>
                            </td>
                        </tr>
                    </tfoot>
                </table>
            </div>

            <b-form-group
                class="mt-2"
                label="Description"
            >
                <b-form-textarea
                    v-model="rubric.description"
                    placeholder="Description"
                    rows="5"
                />
            </b-form-group>

            <b-form-group label="Visibility">
                <b-form-select
                    v-model="rubric.visibility"
                    :options="[
                        {
                            value: 'h',
                            text: 'Hidden from students',
                        },
                        {
                            value: 'v',
                            text: 'Visible to students',
                        },
                        {
                            value: 'huv',
                            text: 'Hidden untill overall feedback is provided',
                        },
                    ]"
                />
            </b-form-group>

            <b-form-group
                v-if="['v', 'huv'].includes(rubric.visibility)"
                label="Hide score from students"
                description="When students preview the rubric, the scoring configuration will be hidden."
            >
                <b-form-radio-group
                    v-model="rubric.hide_score_from_students"
                    class="theme-boolean-radio"
                    :options="[
                        {
                            value: true,
                            text: 'Yes',
                        },
                        {
                            value: false,
                            text: 'No',
                        },
                    ]"
                    name="radios-btn-default"
                    buttons
                />
            </b-form-group>
        </b-form>

        <template
            v-if="!readMode"
            #footer
        >
            <b-button
                class="green-button float-right"
                type="submit"
                form="rubricEditForm"
            >
                <icon :name="(create) ? 'plus' : 'save'"/>
                {{ (create) ? 'Add Rubric' : 'Save' }}
            </b-button>
        </template>
    </b-card>
</template>

<script>
import CriterionEdit from '@/components/rubric/CriterionEdit.vue'
import LevelEdit from '@/components/rubric/LevelEdit.vue'
import RubricReadMode from '@/components/rubric/RubricReadMode.vue'

import { mapActions, mapGetters, mapMutations } from 'vuex'

export default {
    components: {
        CriterionEdit,
        LevelEdit,
        RubricReadMode,
        // RubricEditLayout,
    },
    props: {
        rubric: {
            required: true,
            type: Object,
        },
    },
    data () {
        return {
            nameInvalidFeedback: null,
            nameInputState: null,
            newCriterionId: -1,
        }
    },
    computed: {
        ...mapGetters({
            readMode: 'assignmentEditor/readMode',
            rubrics: 'rubric/assignmentRubrics',
        }),
        create () { return this.rubric.id < 0 },
        criteriaMaxLevelLength () {
            return Math.max(...this.rubric.criteria.map((criterion) => criterion.levels.length))
        },
        criteriaMinId () {
            return Math.min(...this.rubric.criteria.map((criterion) => criterion.id), 0)
        },
        /* Each criterion adds a number of points to the total of the rubric.
         * The score of a criterion's level should be divided from full points to no points (max to min) */
        pointSum () {
            let sum = 0

            this.rubric.criteria.forEach((criterion) => {
                let criterionPointMax = 0

                criterion.levels.forEach((level) => {
                    const levelPoints = parseInt(level.points, 10)
                    if (levelPoints > criterionPointMax) {
                        criterionPointMax = levelPoints
                    }
                })

                sum += criterionPointMax
            })

            return sum
        },
    },
    watch: {
        'rubric.name': 'validateNameInput',
    },
    methods: {
        ...mapMutations({
            setModeToEdit: 'assignmentEditor/SET_ACTIVE_COMPONENT_MODE_TO_EDIT',
            setModeToRead: 'assignmentEditor/SET_ACTIVE_COMPONENT_MODE_TO_READ',
        }),
        ...mapActions({
            cancelRubricEdit: 'assignmentEditor/cancelRubricEdit',
            rubricCreated: 'assignmentEditor/rubricCreated',
            rubricDeleted: 'assignmentEditor/rubricDeleted',
            rubricUpdated: 'assignmentEditor/rubricUpdated',
            createRubric: 'rubric/create',
            updateRubric: 'rubric/update',
            deleteRubric: 'rubric/delete',
        }),
        addCriterion () {
            this.rubric.criteria.push({
                id: this.criteriaMinId - 1,
                name: `Criteria ${this.rubric.criteria.length + 1}`,
                description: '',
                long_description: '',
                score_as_range: false,
                location: this.rubric.criteria.length,
                levels: [
                    {
                        name: 'Full marks',
                        points: 10,
                        location: 0,
                    },
                    {
                        name: 'No marks',
                        points: 0,
                        location: 1,
                    },
                ],
            })
        },
        floatFormatter (value) {
            if (value === '') { return 0 }
            return parseFloat(value)
        },
        validateNameInput () {
            const name = this.rubric.name

            if (name === '') {
                this.nameInvalidFeedback = 'Name cannot be empty.'
                this.nameInputState = false
            } else if (this.rubrics.some((elem) => elem.id !== this.rubric.id && elem.name === name)) {
                this.nameInvalidFeedback = 'Name is not unique.'
                this.nameInputState = false
            } else {
                this.nameInputState = null
            }
        },
        finalizeRubricChanges () {
            if (!this.validateData()) { return }

            if (this.create) {
                this.createRubric({ rubric: this.rubric, aID: this.$route.params.aID })
                    .then((rubric) => {
                        this.rubricCreated({ rubric, fromPresetNode: this.rubric.fromPresetNode })
                    })
            } else {
                this.updateRubric({ id: this.rubric.id, data: this.rubric, aID: this.$route.params.aID })
                    .then((updatedRubric) => {
                        this.rubricUpdated({ updatedRubric, oldRubricId: this.rubric.id })
                    })
            }
        },
        confirmDeleteRubric () {
            if (window.confirm(
                `Are you sure you want to delete rubric "${this.rubric.name}" from the assignment?`)) {
                this.deleteRubric({ id: this.rubric.id, aID: this.$route.params.aID })
                    .then(() => { this.rubricDeleted({ rubric: this.rubric }) })
            }
        },
    },
}
</script>

<style lang="sass">
%remove-default-table-styling
    margin: 0
    padding: 0
    border: 0
    font-size: 100%
    font: inherit
    vertical-align: top

.rubric-edit
    & > table, caption, tbody, tfoot, thead, tr, th, td
        @extend %remove-default-table-styling

    & > table
        border-collapse: collapse
        border-spacing: 0

    th, td
        padding: 10px
        text-align: left
        border: 1px solid #ccc

    .main-column-headers
        font-weight: bold

    .oneline
        white-space: nowrap

    .criterion-cell
        min-width: 150px

    .levels-cell-table-container  // Outer container where the levels table is nested
        padding: 0px
        height: 250px // We have to define the heigth for the nested table to scale its heigth relative to this

    .levels
        & > table
            height: 100%

        & > table, caption, tbody, tfoot, thead, tr, th, td
            border: 0

        tr > td
            &:not(:first-child)
                border-left: 1px dashed #ccc
            &:not(:last-child)
                border-right: 1px dashed #ccc

        // TODO: Fix messy css
        .level-container
            display: flex
            height: 100%
            min-width: 200px
            align-items: stretch
            flex: 1
            flex-direction: row
            flex-wrap: nowrap

            .level-main-content
                position: relative
                min-width: 150px
                flex-direction: column
                flex: 1
                // Create some extra spacing for the add level icon
                &:not(:last-child)
                    margin-right: 5px
                &:not(:first-child)
                    margin-left: 5px

            .add-level
                flex-direction: column
                display: flex
                justify-content: center
                margin-right: -1.1rem // align the icon on top of the table cell border
</style>
