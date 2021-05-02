<template>
    <b-row>
        <b-col xl="4">
            <b-form-group
                :invalid-feedback="unlockDateInvalidFeedback"
                :state="unlockDateInputState"
                :class="{ 'mb-2': $root.lgMax}"
            >
                <template #label>
                    Unlock date
                    <tooltip tip="Students will be able to work on the assignment from this date onwards"/>
                </template>

                <reset-wrapper v-model="assignment.unlock_date">
                    <flat-pickr
                        v-model="assignment.unlock_date"
                        :config="unlockDateConfig"
                    />
                </reset-wrapper>
            </b-form-group>
        </b-col>

        <b-col xl="4">
            <b-form-group
                :invalid-feedback="dueDateInvalidFeedback"
                :state="dueDateInputState"
                :class="{ 'mb-2': $root.lgMax}"
            >
                <template #label>
                    Due date
                    <tooltip
                        tip="Students are expected to have finished their assignment by this date, but new entries
                        can still be added until the lock date"
                    />
                </template>

                <reset-wrapper v-model="assignment.due_date">
                    <flat-pickr
                        v-model="assignment.due_date"
                        :config="dueDateConfig"
                    />
                </reset-wrapper>
            </b-form-group>
        </b-col>

        <b-col xl="4">
            <b-form-group
                :invalid-feedback="lockDateInvalidFeedback"
                :state="lockDateInputState"
            >
                <template #label>
                    Lock date
                    <tooltip tip="No more entries can be added after this date"/>
                </template>

                <reset-wrapper v-model="assignment.lock_date">
                    <flat-pickr
                        v-model="assignment.lock_date"
                        :config="lockDateConfig"
                    />
                </reset-wrapper>
            </b-form-group>
        </b-col>
    </b-row>
</template>

<script>
import tooltip from '@/components/assets/Tooltip.vue'

export default {
    name: 'AssignmentDetailsDates',
    components: {
        tooltip,
    },
    props: {
        assignment: {
            required: true,
        },
        presetNodes: {
            default: () => [],
        },
    },
    data () {
        return {
            unlockDateInputState: null,
            unlockDateInvalidFeedback: null,
            dueDateInputState: null,
            dueDateInvalidFeedback: null,
            lockDateInputState: null,
            lockDateInvalidFeedback: null,
        }
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

            if (this.assignment.due_date && (!additionalConfig.maxDate
                || new Date(this.assignment.due_date) < additionalConfig.maxDate)) {
                // Assignment has due date earlier than current max.
                additionalConfig.maxDate = new Date(this.assignment.due_date)
            } else if (this.assignment.lock_date && (!additionalConfig.maxDate
                || new Date(this.assignment.lock_date) < additionalConfig.maxDate)) {
                // Assignment has lock date earlier than current max.
                additionalConfig.maxDate = new Date(this.assignment.lock_date)
            }

            return { ...additionalConfig, ...this.$root.flatPickrTimeConfig }
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

            if (this.assignment.unlock_date && (!additionalConfig.minDate
                || new Date(this.assignment.unlock_date) > additionalConfig.minDate)) {
                // Assignment has unlock date later than current min.
                additionalConfig.minDate = new Date(this.assignment.unlock_date)
            }

            if (this.assignment.lock_date) {
                // Assignment has lock date, due date cannot be later.
                additionalConfig.maxDate = new Date(this.assignment.lock_date)
            }

            return { ...additionalConfig, ...this.$root.flatPickrTimeConfig }
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

            if (this.assignment.due_date && (!additionalConfig.minDate
                || new Date(this.assignment.due_date) > additionalConfig.minDate)) {
                // Assignment has due date later than current min.
                additionalConfig.minDate = new Date(this.assignment.due_date)
            } else if (this.assignment.unlock_date && (!additionalConfig.minDate
                || new Date(this.assignment.unlock_date) > additionalConfig.minDate)) {
                // Assignment has unlock date later than current min.
                additionalConfig.minDate = new Date(this.assignment.unlock_date)
            }

            return { ...additionalConfig, ...this.$root.flatPickrTimeConfig }
        },
    },
    watch: {
        'assignment.unlock_date': 'validateUnlockDateInput',
        'assignment.due_date': 'validateDueDateInput',
        'assignment.lock_date': 'validateLockDateInput',
    },
    methods: {
        firstAfterSecond (first, second) {
            return first && second && Date.parse(first) > Date.parse(second)
        },
        firstBeforeSecond (first, second) {
            return first && second && Date.parse(first) < Date.parse(second)
        },
        validateUnlockDateInput () {
            const unlockDate = this.assignment.unlock_date

            if (this.firstAfterSecond(unlockDate, this.assignment.due_date)) {
                this.unlockDateInputState = false
                this.unlockDateInvalidFeedback = 'After due date.'
            } else if (this.firstAfterSecond(unlockDate, this.assignment.lock_date)) {
                this.unlockDateInputState = false
                this.unlockDateInvalidFeedback = 'After lock date.'
            } else if (this.presetNodes.some((preset) => this.firstAfterSecond(unlockDate, preset.unlock_date))) {
                this.unlockDateInputState = false
                this.unlockDateInvalidFeedback = 'Unlocks after one or more deadlines unlock.'
            } else if (this.presetNodes.some((preset) => this.firstAfterSecond(unlockDate, preset.due_date))) {
                this.unlockDateInputState = false
                this.unlockDateInvalidFeedback = 'Unlocks after one or more deadlines are due.'
            } else if (this.presetNodes.some((preset) => this.firstAfterSecond(unlockDate, preset.lock_date))) {
                this.unlockDateInputState = false
                this.unlockDateInvalidFeedback = 'Unlocks after one or more deadlines are locked.'
            } else {
                this.unlockDateInputState = null
            }
        },
        validateDueDateInput () {
            const dueDate = this.assignment.due_date

            if (this.firstBeforeSecond(dueDate, this.assignment.unlock_date)) {
                this.dueDateInputState = false
                this.dueDateInvalidFeedback = 'Before unlock date.'
            } else if (this.firstAfterSecond(dueDate, this.assignment.lock_date)) {
                this.dueDateInputState = false
                this.dueDateInvalidFeedback = 'After lock date.'
            } else if (this.presetNodes.some((preset) => this.firstBeforeSecond(dueDate, preset.unlock_date))) {
                this.unlockDateInputState = false
                this.unlockDateInvalidFeedback = 'Due before one or more deadlines unlock.'
            } else if (this.presetNodes.some((preset) => this.firstBeforeSecond(dueDate, preset.due_date))) {
                this.unlockDateInputState = false
                this.unlockDateInvalidFeedback = 'Due before one or more deadlines are due.'
            } else {
                this.dueDateInputState = null
            }
        },
        validateLockDateInput () {
            const lockDate = this.assignment.lock_date

            if (this.firstBeforeSecond(lockDate, this.assignment.unlock_date)) {
                this.lockDateInputState = false
                this.lockDateInvalidFeedback = 'Before unlock date.'
            } else if (this.firstBeforeSecond(lockDate, this.assignment.due_date)) {
                this.lockDateInputState = false
                this.lockDateInvalidFeedback = 'Before due date.'
            } else if (this.presetNodes.some((preset) => this.firstBeforeSecond(lockDate, preset.unlock_date))) {
                this.unlockDateInputState = false
                this.unlockDateInvalidFeedback = 'Locks before one or more deadlines unlock.'
            } else if (this.presetNodes.some((preset) => this.firstBeforeSecond(lockDate, preset.due_date))) {
                this.unlockDateInputState = false
                this.unlockDateInvalidFeedback = 'Due before one or more deadlines are due.'
            } else if (this.presetNodes.some((preset) => this.firstBeforeSecond(lockDate, preset.lock_date))) {
                this.unlockDateInputState = false
                this.unlockDateInvalidFeedback = 'Locks before one or more deadlines lock.'
            } else {
                this.lockDateInputState = null
            }
        },
    },
}
</script>
