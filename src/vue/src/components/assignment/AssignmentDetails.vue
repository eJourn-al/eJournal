<template>
    <load-wrapper :loading="assignmentDetails === null">
        <template v-if="assignmentDetails !== null">
            <b-form-group
                label="Name"
                class="required"
                :invalid-feedback="nameInvalidFeedback"
                :state="nameInputState"
            >
                <b-input-group>
                    <b-input
                        v-model="assignmentDetails.name"
                        placeholder="Assignment name"
                        trim
                        required
                        :state="nameInputState"
                    />

                    <b-button
                        v-b-tooltip:hover="
                            `This assignment is visible ${(assignmentDetails.is_published)? '' : 'not'} to students`
                        "
                        class="ml-2"
                        :class="(assignmentDetails.is_published) ? 'green-button' : 'red-button'"
                        @click="assignmentDetails.is_published = !assignmentDetails.is_published"
                    >
                        <icon :name="(assignmentDetails.is_published) ? 'check' : 'times'"/>
                        {{ (assignmentDetails.is_published) ? 'Published' : 'Unpublished' }}
                    </b-button>
                </b-input-group>
            </b-form-group>

            <b-form-group label="Description">
                <text-editor
                    :id="`text-editor-assignment-edit-description-${assignmentDetails.id}`"
                    :key="`text-editor-assignment-edit-description-${assignmentDetails.id}`"
                    ref="text-editor-assignment-edit-description"
                    v-model="assignmentDetails.description"
                    :footer="false"
                    placeholder="Description of the assignment"
                />
            </b-form-group>

            <b-form-group
                class="required"
                :state="pointsPossibleInputState"
                :invalid-feedback="pointsPossibleInvalidFeedback"
            >
                <template #label>
                    Points possible
                    <tooltip
                        tip="The number of points that represents a perfect score for this assignment, excluding
                        bonus points"
                    />
                </template>

                <b-input
                    v-model="assignmentDetails.points_possible"
                    placeholder="Points"
                    type="number"
                    required
                    step="1"
                    :min="minimumPointsPossible"
                />
            </b-form-group>

            <template
                v-if="assignmentDetails.id && assignmentDetails.all_groups"
            >
                <h2 class="theme-h2 field-heading">
                    Assign to
                    <tooltip
                        tip="This setting determines for which course groups the assignment is visible"
                    />
                </h2>
                <theme-select
                    v-model="assignmentDetails.assigned_groups"
                    label="name"
                    trackBy="id"
                    :options="assignmentDetails.all_groups !== undefined ? assignmentDetails.all_groups : []"
                    :multiple="true"
                    :searchable="true"
                    :multiSelectText="`group${assignmentDetails.assigned_groups &&
                        assignmentDetails.assigned_groups.length === 1 ? '' : 's'} assigned`"
                    placeholder="Everyone"
                    class="mb-2 mr-2"
                />
            </template>

            <assignment-details-dates
                ref="assignmentDetailsDates"
                :assignment="assignmentDetails"
                :presetNodes="presetNodes"
            />

            <div
                v-if="assignmentDetails.is_group_assignment
                    || !assignmentDetails.id
                    || assignmentDetails.can_change_type"
                class="bordered-content p-3 mt-3"
            >
                <radio-button
                    v-model="assignmentDetails.is_group_assignment"
                    :class="{ 'input-disabled': assignmentDetails.id && !assignmentDetails.can_change_type }"
                    :options="[
                        {
                            value: true,
                            icon: 'check',
                            class: 'green-button',
                        },
                        {
                            value: false,
                            icon: 'times',
                            class: 'red-button',
                        },
                    ]"
                    class="float-right mb-2 ml-2"
                />
                <h2 class="theme-h2 field-heading mb-2">
                    Group assignment
                </h2>
                <small>
                    Have multiple students contribute to a shared journal.
                    Selecting this option requires you to create journals on the assignment page for students to join.
                </small>
            </div>
            <div
                v-if="assignmentDetails.is_group_assignment"
                class="background-light-grey round-border p-3 mt-2"
            >
                <radio-button
                    v-model="assignmentDetails.can_lock_journal"
                    :options="[
                        {
                            value: true,
                            icon: 'check',
                            class: 'green-button',
                        },
                        {
                            value: false,
                            icon: 'times',
                            class: 'red-button',
                        },
                    ]"
                    class="float-right mb-2 ml-2"
                />
                <h2 class="theme-h2 field-heading mb-2">
                    Allow locking for journal members
                </h2>
                <small>
                    Once the members of a journal are locked, it cannot be joined by other students.
                    Teachers can still manually add students to a journal.
                </small>
                <hr/>
                <radio-button
                    v-model="assignmentDetails.can_set_journal_name"
                    :options="[
                        {
                            value: true,
                            icon: 'check',
                            class: 'green-button',
                        },
                        {
                            value: false,
                            icon: 'times',
                            class: 'red-button',
                        },
                    ]"
                    class="float-right mb-2 ml-2"
                />
                <h2 class="theme-h2 field-heading">
                    Allow custom journal name
                </h2>
                <small>
                    Allow members of a journal to override its given name.
                </small>
                <hr/>
                <radio-button
                    v-model="assignmentDetails.can_set_journal_image"
                    :options="[
                        {
                            value: true,
                            icon: 'check',
                            class: 'green-button',
                        },
                        {
                            value: false,
                            icon: 'times',
                            class: 'red-button',
                        },
                    ]"
                    class="float-right mb-2 ml-2"
                />
                <h2 class="theme-h2 field-heading">
                    Allow custom display picture
                </h2>
                <small>
                    Allow members of a journal to override its display picture.
                </small>
                <hr/>
                <radio-button
                    v-model="assignmentDetails.remove_grade_upon_leaving_group"
                    :options="[
                        {
                            value: true,
                            icon: 'check',
                            class: 'green-button',
                        },
                        {
                            value: false,
                            icon: 'times',
                            class: 'red-button',
                        },
                    ]"
                    class="float-right mb-2 ml-2"
                />
                <h2 class="theme-h2 field-heading mb-2">
                    Reset grade when leaving journal
                </h2>
                <small>
                    Reset the grade of a student to 0 if they leave (or are removed from) a journal.
                </small>
            </div>
        </template>
    </load-wrapper>
</template>

<script>
import AssignmentDetailsDates from '@/components/assignment/AssignmentDetailsDates.vue'
import LoadWrapper from '@/components/loading/LoadWrapper.vue'
import RadioButton from '@/components/assets/RadioButton.vue'
import tooltip from '@/components/assets/Tooltip.vue'

export default {
    name: 'AssignmentDetails',
    components: {
        textEditor: () => import(/* webpackChunkName: 'text-editor' */ '@/components/assets/TextEditor.vue'),
        tooltip,
        AssignmentDetailsDates,
        LoadWrapper,
        RadioButton,
    },
    props: {
        assignmentDetails: {
            required: true,
        },
        presetNodes: {
            // Props with type Object/Array must use a factory function to return the default value.
            default: () => [],
        },
    },
    data () {
        return {
            nameInputState: null,
            nameInvalidFeedback: null,
            pointsPossibleInputState: null,
            pointsPossibleInvalidFeedback: null,

            validators: [],
        }
    },
    computed: {
        minimumPointsPossible () {
            let min = 0

            this.presetNodes.forEach((preset) => {
                if (preset.type === 'p') {
                    min = Math.max(min, preset.target)
                }
            })

            return min
        },
    },
    watch: {
        'assignmentDetails.name': 'validateNameInput',
        'assignmentDetails.points_possible': 'validatePointsPossibleInput',
    },
    methods: {
        validateNameInput () {
            const name = this.assignmentDetails.name

            if (name === '') {
                this.nameInputState = false
                this.nameInvalidFeedback = 'Name cannot be empty.'
            } else {
                this.nameInputState = null
            }
        },
        validatePointsPossibleInput () {
            const points = this.assignmentDetails.points_possible

            if (points === '') {
                this.pointsPossibleInputState = false
                this.pointsPossibleInvalidFeedback = 'Points possible is required.'
            } else if (points < 0) {
                this.pointsPossibleInputState = false
                this.pointsPossibleInvalidFeedback = 'Points possible should a be positive number.'
            } else if (points < this.minimumPointsPossible) {
                this.pointsPossibleInputState = false
                this.pointsPossibleInvalidFeedback = `
                    A progress goal exists which requires ${this.minimumPointsPossible} points.
                `
            } else {
                this.pointsPossibleInputState = null
            }
        },
    },
}
</script>
