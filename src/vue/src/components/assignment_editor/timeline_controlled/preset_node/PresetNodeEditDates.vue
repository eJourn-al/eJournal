<template>
    <b-row>
        <b-col
            v-if="deadline"
            xl="4"
        >
            <b-form-group
                :invalid-feedback="unlockDateInvalidFeedback"
                :state="unlockDateInputState"
                :class="{ 'multi-form': $root.lgMax}"
            >
                <template #label>
                    Unlock date
                    <tooltip tip="Students will be able to work on the entry from this date onwards"/>
                </template>

                <reset-wrapper v-model="presetNode.unlock_date">
                    <flat-pickr
                        v-model="presetNode.unlock_date"
                        class="full-width"
                        required
                        :config="unlockDateConfig"
                    />
                </reset-wrapper>
            </b-form-group>
        </b-col>

        <b-col :xl="(deadline) ? 4 : 12">
            <b-form-group
                :invalid-feedback="dueDateInvalidFeedback"
                :state="dueDateInputState"
                class="required multi-form"
            >
                <template #label>
                    Due date
                    <tooltip :tip="dueDateTooltip"/>
                </template>

                <reset-wrapper v-model="presetNode.due_date">
                    <flat-pickr
                        v-model="presetNode.due_date"
                        class="full-width"
                        required
                        :config="(deadline) ? dueDateConfig: progressDateConfig"
                    />
                </reset-wrapper>
            </b-form-group>
        </b-col>

        <b-col
            v-if="deadline"
            xl="4"
        >
            <b-form-group
                :invalid-feedback="lockDateInvalidFeedback"
                :state="lockDateInputState"
                class="multi-form"
            >
                <template #label>
                    Lock date
                    <tooltip tip="Students will not be able to fill in the entry anymore after this date"/>
                </template>

                <reset-wrapper v-model="presetNode.lock_date">
                    <flat-pickr
                        v-model="presetNode.lock_date"
                        class="full-width"
                        required
                        :config="lockDateConfig"
                    />
                </reset-wrapper>
            </b-form-group>
        </b-col>
    </b-row>
</template>

<script>
import Tooltip from '@/components/assets/Tooltip.vue'

import { mapGetters } from 'vuex'

export default {
    components: {
        Tooltip,
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
        ...mapGetters({
            templates: 'template/assignmentTemplates',
            assignment: 'assignment/assignment',
            presetNode: 'assignmentEditor/selectedPresetNode',
        }),
        deadline () {
            return this.presetNode.type === 'd'
        },
        dueDateTooltip () {
            if (this.deadline) {
                return `
                    Students are expected to have finished their entry by this date, but new entries
                    can still be added until the lock date
                `
            }
            return `
                Students are expected to have reached the number of points below by this date,
                but new entries can still be added until the assignment lock date
            `
        },
        // Ensure the unlock date is between the assignment unlock date and before preset due / lock date and
        // assignment due / lock date .
        unlockDateConfig () {
            const additionalConfig = {}

            if (this.presetNode.due_date) {
                additionalConfig.maxDate = new Date(this.presetNode.due_date)
            } else if (this.presetNode.lock_date) {
                additionalConfig.maxDate = new Date(this.presetNode.lock_date)
            } else if (this.assignment.lock_date) {
                additionalConfig.maxDate = new Date(this.assignment.lock_date)
            }

            // Assignment due date can be before the current preset lock date.
            if (this.assignment.due_date && (!additionalConfig.maxDate
                || new Date(this.assignment.due_date) < additionalConfig.maxDate)) {
                additionalConfig.maxDate = new Date(this.assignment.due_date)
            }

            if (this.assignment.unlock_date) {
                additionalConfig.minDate = new Date(this.assignment.unlock_date)
            }

            return { ...additionalConfig, ...this.$root.flatPickrTimeConfig }
        },
        // Ensure the due date is preset unlock / lock date and between the assignment unlock and due / lock date.
        dueDateConfig () {
            const additionalConfig = {}

            if (this.presetNode.unlock_date) {
                additionalConfig.minDate = new Date(this.presetNode.unlock_date)
            } if (this.assignment.unlock_date) {
                additionalConfig.minDate = new Date(this.assignment.unlock_date)
            }

            if (this.presetNode.lock_date) {
                additionalConfig.maxDate = new Date(this.presetNode.lock_date)
            } else if (this.assignment.lock_date) {
                additionalConfig.maxDate = new Date(this.assignment.lock_date)
            }

            // Assignment due date can be before the current preset lock date.
            if (this.assignment.due_date && (!additionalConfig.maxDate
                || new Date(this.assignment.due_date) < additionalConfig.maxDate)) {
                additionalConfig.maxDate = new Date(this.assignment.due_date)
            }

            return { ...additionalConfig, ...this.$root.flatPickrTimeConfig }
        },
        // Ensure the lock date is after the preset unlock / due date and betwween the assignment unlock / due and lock
        // date.
        lockDateConfig () {
            const additionalConfig = {}

            if (this.presetNode.due_date) {
                additionalConfig.minDate = new Date(this.presetNode.due_date)
            } else if (this.presetNode.unlock_date) {
                additionalConfig.minDate = new Date(this.presetNode.unlock_date)
            } else if (this.assignment.unlock_date) {
                additionalConfig.minDate = new Date(this.assignment.unlock_date)
            }

            if (this.assignment.lock_date) {
                additionalConfig.maxDate = new Date(this.assignment.lock_date)
            }

            return { ...additionalConfig, ...this.$root.flatPickrTimeConfig }
        },
        // Ensure the progress date is between the assignment unlock and due / lock date.
        progressDateConfig () {
            const additionalConfig = {}

            if (this.assignment.unlock_date) {
                additionalConfig.minDate = new Date(this.assignment.unlock_date)
            }

            if (this.assignment.due_date) {
                additionalConfig.maxDate = new Date(this.assignment.due_date)
            } else if (this.assignment.lock_date) {
                additionalConfig.maxDate = new Date(this.assignment.lock_date)
            }

            return { ...additionalConfig, ...this.$root.flatPickrTimeConfig }
        },
    },
    watch: {
        'presetNode.unlock_date': {
            handler (unlockDate) {
                this.checkUnlockDate(unlockDate)
                this.checkDueDate(this.presetNode.due_date)
                this.checkLockDate(this.presetNode.lock_date)
            },
        },
        'presetNode.due_date': {
            handler (dueDate) {
                this.checkUnlockDate(this.presetNode.unlock_date)
                this.checkDueDate(dueDate)
                this.checkLockDate(this.presetNode.lock_date)
            },
        },
        'presetNode.lock_date': {
            handler (lockDate) {
                this.checkUnlockDate(this.presetNode.unlock_date)
                this.checkDueDate(this.presetNode.due_date)
                this.checkLockDate(lockDate)
            },
        },
    },
    methods: {
        firstAfterSecond (first, second) {
            return first && second && Date.parse(first) > Date.parse(second)
        },
        firstBeforeSecond (first, second) {
            return first && second && Date.parse(first) < Date.parse(second)
        },
        checkUnlockDate (unlockDate) {
            if (this.firstBeforeSecond(unlockDate, this.assignment.unlock_date)) {
                this.unlockDateInputState = false
                this.unlockDateInvalidFeedback = 'Before assignment unlocks.'
            } else if (this.firstAfterSecond(unlockDate, this.assignment.due_date)) {
                this.unlockDateInputState = false
                this.unlockDateInvalidFeedback = 'After assignment is due.'
            } else if (this.firstAfterSecond(unlockDate, this.assignment.lock_date)) {
                this.unlockDateInputState = false
                this.unlockDateInvalidFeedback = 'After assignment is locked.'
            } else if (this.firstAfterSecond(unlockDate, this.presetNode.due_date)) {
                this.unlockDateInputState = false
                this.unlockDateInvalidFeedback = 'Unlocked after due date.'
            } else if (this.firstAfterSecond(unlockDate, this.presetNode.lock_date)) {
                this.unlockDateInputState = false
                this.unlockDateInvalidFeedback = 'Unlocked after lock date.'
            } else {
                this.unlockDateInputState = null
            }
        },
        checkDueDate (dueDate) {
            if (this.firstBeforeSecond(dueDate, this.assignment.unlock_date)) {
                this.dueDateInputState = false
                this.dueDateInvalidFeedback = 'Before assignment unlocks.'
            } else if (this.firstAfterSecond(dueDate, this.assignment.due_date)) {
                this.dueDateInputState = false
                this.dueDateInvalidFeedback = 'After assignment is due.'
            } else if (this.firstAfterSecond(dueDate, this.assignment.lock_date)) {
                this.dueDateInputState = false
                this.dueDateInvalidFeedback = 'After assignment locks.'
            } else if (this.firstBeforeSecond(dueDate, this.presetNode.unlock_date)) {
                this.dueDateInputState = false
                this.dueDateInvalidFeedback = 'Before unlock date.'
            } else if (this.firstAfterSecond(dueDate, this.presetNode.lock_date)) {
                this.dueDateInputState = false
                this.dueDateInvalidFeedback = 'After lock date.'
            } else if (dueDate === '') {
                this.dueDateInputState = false
                this.dueDateInvalidFeedback = 'Due date is required.'
            } else {
                this.dueDateInputState = null
            }
        },
        checkLockDate (lockDate) {
            if (this.firstBeforeSecond(lockDate, this.assignment.unlock_date)) {
                this.lockDateInputState = false
                this.lockDateInvalidFeedback = 'Before assignment unlocks.'
            } else if (this.firstAfterSecond(lockDate, this.assignment.due_date)) {
                this.lockDateInputState = false
                this.lockDateInvalidFeedback = 'After assignment is due.'
            } else if (this.firstAfterSecond(lockDate, this.assignment.lock_date)) {
                this.lockDateInputState = false
                this.lockDateInvalidFeedback = 'After assignment locks.'
            } else if (this.firstBeforeSecond(lockDate, this.presetNode.unlock_date)) {
                this.lockDateInputState = false
                this.lockDateInvalidFeedback = 'Before unlock date.'
            } else if (this.firstBeforeSecond(lockDate, this.presetNode.due_date)) {
                this.lockDateInputState = false
                this.lockDateInvalidFeedback = 'Before due date.'
            } else {
                this.lockDateInputState = null
            }
        },
    },
}
</script>
