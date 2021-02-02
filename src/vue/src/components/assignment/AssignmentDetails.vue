<template>
    <div>
        <h2 class="theme-h2 field-heading required">
            Name
        </h2>
        <div class="d-flex">
            <b-input
                v-model="assignmentDetails.name"
                class="multi-form theme-input"
                placeholder="Assignment name"
                required
            />
            <b-button
                v-if="assignmentDetails.is_published"
                v-b-tooltip:hover="'This assignment is visible to students'"
                class="green-button multi-form ml-2"
                @click="assignmentDetails.is_published = false"
            >
                <icon name="check"/>
                Published
            </b-button>
            <b-button
                v-if="!assignmentDetails.is_published"
                v-b-tooltip:hover="'This assignment is not visible to students'"

                class="red-button multi-form ml-2"
                @click="assignmentDetails.is_published = true"
            >
                <icon name="times"/>
                Unpublished
            </b-button>
        </div>
        <h2 class="theme-h2 field-heading">
            Description
        </h2>
        <text-editor
            :id="`text-editor-assignment-edit-description-${assignmentDetails.id}`"
            :key="`text-editor-assignment-edit-description-${assignmentDetails.id}`"
            ref="text-editor-assignment-edit-description"
            v-model="assignmentDetails.description"
            :footer="false"
            class="multi-form"
            placeholder="Description of the assignment"
        />
        <h2 class="theme-h2 field-heading required">
            Points possible
            <tooltip
                tip="The number of points that represents a perfect score for this assignment, excluding
                bonus points"
            />
        </h2>
        <b-input
            v-model="assignmentDetails.points_possible"
            class="multi-form theme-input"
            placeholder="Points"
            type="number"
            min="0"
            required
        />
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
                class="multi-form mr-2"
            />
        </template>
        <b-row>
            <b-col xl="4">
                <h2 class="theme-h2 field-heading">
                    Unlock date
                    <tooltip tip="Students will be able to work on the assignment from this date onwards"/>
                </h2>
                <reset-wrapper v-model="assignmentDetails.unlock_date">
                    <flat-pickr
                        v-model="assignmentDetails.unlock_date"
                        class="multi-form"
                        :config="unlockDateConfig"
                    />
                </reset-wrapper>
            </b-col>
            <b-col xl="4">
                <h2 class="theme-h2 field-heading">
                    Due date
                    <tooltip
                        tip="Students are expected to have finished their assignment by this date, but new entries
                        can still be added until the lock date"
                    />
                </h2>
                <reset-wrapper v-model="assignmentDetails.due_date">
                    <flat-pickr
                        v-model="assignmentDetails.due_date"
                        class="multi-form"
                        :config="dueDateConfig"
                    />
                </reset-wrapper>
            </b-col>
            <b-col xl="4">
                <h2 class="theme-h2 field-heading">
                    Lock date
                    <tooltip tip="No more entries can be added after this date"/>
                </h2>
                <reset-wrapper v-model="assignmentDetails.lock_date">
                    <flat-pickr
                        v-model="assignmentDetails.lock_date"
                        class="multi-form"
                        :config="lockDateConfig"
                    />
                </reset-wrapper>
            </b-col>
        </b-row>
        <b-card
            v-if="assignmentDetails.is_group_assignment || !assignmentDetails.id || assignmentDetails.can_change_type"
            class="no-hover"
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
            <h2 class="theme-h2 field-heading multi-form">
                Group assignment
            </h2>
            Have multiple students contribute to a shared journal.
            Selecting this option requires you to create journals on the assignment page for students to join.
            <template v-if="assignmentDetails.is_group_assignment">
                <hr/>
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
                <h2 class="theme-h2 field-heading multi-form">
                    Allow locking for journal members
                </h2>
                Once the members of a journal are locked, it cannot be joined by other students.
                Teachers can still manually add students to a journal.
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
                Allow members of a journal to override its given name.
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
                Allow members of a journal to override its display picture.
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
                <h2 class="theme-h2 field-heading multi-form">
                    Reset grade when leaving journal
                </h2>
                Reset the grade of a student to 0 if they leave (or are removed from) a journal.
            </template>
        </b-card>
    </div>
</template>

<script>
import RadioButton from '@/components/assets/RadioButton.vue'
import tooltip from '@/components/assets/Tooltip.vue'

export default {
    name: 'AssignmentDetails',
    components: {
        textEditor: () => import(/* webpackChunkName: 'text-editor' */ '@/components/assets/TextEditor.vue'),
        tooltip,
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
    computed: {
        // Ensure the unlock date cannot be later than any preset date or the assignment due or lock date.
        unlockDateConfig () {
            const additionalConfig = {}

            this.presetNodes.forEach((node) => {
                if (node.unlock_date && (!additionalConfig.maxDate
                    || new Date(node.unlock_date) < additionalConfig.maxDate)) {
                    // Preset has unlock date earlier than current max.
                    additionalConfig.maxDate = new Date(node.unlock_date)
                } else if (node.due_date && (!additionalConfig.maxDate
                    || new Date(node.due_date) < additionalConfig.maxDate)) {
                    // Preset has due date earlier than current max.
                    additionalConfig.maxDate = new Date(node.due_date)
                } else if (node.lock_date && (!additionalConfig.maxDate
                    || new Date(node.lock_date) < additionalConfig.maxDate)) {
                    // Preset has lock date earlier than current max.
                    additionalConfig.maxDate = node.lock_date
                }
            })

            if (this.assignmentDetails.due_date && (!additionalConfig.maxDate
                || new Date(this.assignmentDetails.due_date) < additionalConfig.maxDate)) {
                // Assignment has due date earlier than current max.
                additionalConfig.maxDate = new Date(this.assignmentDetails.due_date)
            } else if (this.assignmentDetails.lock_date && (!additionalConfig.maxDate
                || new Date(this.assignmentDetails.lock_date) < additionalConfig.maxDate)) {
                // Assignment has lock date earlier than current max.
                additionalConfig.maxDate = new Date(this.assignmentDetails.lock_date)
            }

            return Object.assign({}, additionalConfig, this.$root.flatPickrTimeConfig)
        },
        // Ensure the due date cannot be earlier than any preset date or the assignment unlock date, and no later than
        // the assignnment lock date.
        dueDateConfig () {
            const additionalConfig = {}

            this.presetNodes.forEach((node) => {
                if (node.due_date && (!additionalConfig.minDate
                    || new Date(node.due_date) > additionalConfig.minDate)) {
                    // Preset has due date later than current min.
                    additionalConfig.minDate = new Date(node.due_date)
                }
            })

            if (this.assignmentDetails.unlock_date && (!additionalConfig.minDate
                || new Date(this.assignmentDetails.unlock_date) > additionalConfig.minDate)) {
                // Assignment has unlock date later than current min.
                additionalConfig.minDate = new Date(this.assignmentDetails.unlock_date)
            }

            if (this.assignmentDetails.lock_date) {
                // Assignment has lock date, due date cannot be later.
                additionalConfig.maxDate = new Date(this.assignmentDetails.lock_date)
            }

            return Object.assign({}, additionalConfig, this.$root.flatPickrTimeConfig)
        },
        // Ensure the lock date cannot be earlier than any preset date or the assignment due or unlock date.
        lockDateConfig () {
            const additionalConfig = {}

            this.presetNodes.forEach((node) => {
                if (node.unlock_date && (!additionalConfig.minDate
                    || new Date(node.unlock_date) > additionalConfig.minDate)) {
                    // Preset has unlock date later than current min.
                    additionalConfig.minDate = new Date(node.unlock_date)
                } else if (node.due_date && (!additionalConfig.maxDate
                    || new Date(node.due_date) > additionalConfig.maxDate)) {
                    // Preset has due date later than current min.
                    additionalConfig.minDate = new Date(node.due_date)
                } else if (node.lock_date && (!additionalConfig.minDate
                    || new Date(node.lock_date) > additionalConfig.minDate)) {
                    // Preset has lock date later than current min.
                    additionalConfig.minDate = node.lock_date
                }
            })

            if (this.assignmentDetails.due_date && (!additionalConfig.minDate
                || new Date(this.assignmentDetails.due_date) > additionalConfig.minDate)) {
                // Assignment has due date later than current min.
                additionalConfig.minDate = new Date(this.assignmentDetails.due_date)
            } else if (this.assignmentDetails.unlock_date && (!additionalConfig.minDate
                || new Date(this.assignmentDetails.unlock_date) > additionalConfig.minDate)) {
                // Assignment has unlock date later than current min.
                additionalConfig.minDate = new Date(this.assignmentDetails.unlock_date)
            }

            return Object.assign({}, additionalConfig, this.$root.flatPickrTimeConfig)
        },
    },
    methods: {
        validateDetails () {
            if (!/\S/.test(this.assignmentDetails.name)) {
                this.$toasted.error(
                    'Assignment name is missing.')
                return false
            }

            if (!this.assignmentDetails.points_possible) {
                this.$toasted.error('Points possible is missing.')
                return false
            }

            if (Number.isNaN(parseInt(this.assignmentDetails.points_possible, 10))) {
                this.$toasted.error('Points possible is not a valid number.')
                return false
            }

            if (this.assignmentDetails.unlock_date && this.assignmentDetails.due_date
                && Date.parse(this.assignmentDetails.unlock_date) > Date.parse(this.assignmentDetails.due_date)) {
                this.$toasted.error('The assignment is due before the unlock date.')
                return false
            }
            if (this.assignmentDetails.unlock_date && this.assignmentDetails.lock_date
                && Date.parse(this.assignmentDetails.unlock_date) > Date.parse(this.assignmentDetails.lock_date)) {
                this.$toasted.error('The assignment lock date is before the unlock date.')
                return false
            }
            if (this.assignmentDetails.due_date && this.assignmentDetails.lock_date
                && Date.parse(this.assignmentDetails.due_date) > Date.parse(this.assignmentDetails.lock_date)) {
                this.$toasted.error('The assignment lock date is before the due date.')
                return false
            }

            return true
        },
    },
}
</script>
