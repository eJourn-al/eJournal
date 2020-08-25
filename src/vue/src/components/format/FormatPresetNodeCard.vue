<!--
    Editor for the currently selected preset in the format editor.
    Edits the preset prop directly.
    Various (many!) elements emit a changed event to track whether unsaved changes exist.
-->

<template>
    <b-card
        :class="$root.getBorderClass($route.params.cID)"
        class="no-hover overflow-x-hidden"
    >
        <h2
            v-if="!newPreset"
            class="theme-h2 d-inline multi-form"
        >
            <span v-if="currentPreset.type == 'd'">Entry</span>
            <span v-if="currentPreset.type == 'p'">Progress goal</span>
        </h2>

        <b-row v-if="currentPreset.type == 'd'">
            <b-col xl="4">
                <h2 class="theme-h2 field-heading">
                    Unlock date
                    <tooltip tip="Students will be able to work on the entry from this date onwards"/>
                </h2>
                <reset-wrapper v-model="currentPreset.unlock_date">
                    <flat-pickr
                        v-model="currentPreset.unlock_date"
                        class="multi-form full-width"
                        :config="unlockDateConfig"
                    />
                </reset-wrapper>
            </b-col>
            <b-col xl="4">
                <h2 class="theme-h2 field-heading required">
                    Due date
                    <tooltip
                        tip="Students are expected to have finished their entry by this date, but new entries can
                        still be added until the lock date"
                    />
                </h2>
                <reset-wrapper v-model="currentPreset.due_date">
                    <flat-pickr
                        v-model="currentPreset.due_date"
                        class="multi-form full-width"
                        :config="dueDateConfig"
                        @on-change="$emit('change-due-date')"
                    />
                </reset-wrapper>
            </b-col>
            <b-col xl="4">
                <h2 class="theme-h2 field-heading">
                    Lock date
                    <tooltip tip="Students will not be able to fill in the entry anymore after this date"/>
                </h2>
                <reset-wrapper v-model="currentPreset.lock_date">
                    <flat-pickr
                        v-model="currentPreset.lock_date"
                        class="multi-form full-width"
                        :config="lockDateConfig"
                    />
                </reset-wrapper>
            </b-col>
        </b-row>
        <div v-else>
            <h2 class="theme-h2 field-heading required">
                Due date
                <tooltip
                    tip="Students are expected to have reached the amount of points below by this date,
                    but new entries can still be added until the assignment lock date"
                />
            </h2>
            <reset-wrapper v-model="currentPreset.due_date">
                <flat-pickr
                    v-model="currentPreset.due_date"
                    class="multi-form full-width"
                    :config="progressDateConfig"
                    @on-change="$emit('change-due-date')"
                />
            </reset-wrapper>
        </div>

        <h2 class="theme-h2 field-heading">
            Description
        </h2>
        <text-editor
            :id="`preset-description-${currentPreset.id}`"
            :key="`preset-description-${currentPreset.id}`"
            v-model="currentPreset.description"
            class="multi-form"
            placeholder="Description"
            footer="false"
        />

        <div v-if="currentPreset.type === 'd'">
            <h2 class="theme-h2 field-heading required">
                Preset Template
                <tooltip tip="The template students can use for this entry"/>
            </h2>
            <div class="d-flex">
                <b-form-select
                    v-model="currentPreset.template"
                    class="theme-select multi-form mr-2"
                    :class="{ 'input-disabled' : templates.length === 0 }"
                >
                    <option
                        disabled
                        value=""
                    >
                        Please select a template
                    </option>
                    <option
                        v-for="template in templates"
                        :key="template.id"
                        :value="template"
                    >
                        {{ template.name }}
                    </option>
                </b-form-select>
                <b-button
                    v-if="showTemplatePreview"
                    class="multi-form delete-button flex-shrink-0"
                    @click="showTemplatePreview = false"
                >
                    <icon name="eye-slash"/>
                    Hide Preview
                </b-button>
                <b-button
                    v-if="!showTemplatePreview"
                    class="multi-form add-button flex-shrink-0"
                    @click="showTemplatePreview = true"
                >
                    <icon name="eye"/>
                    Show Preview
                </b-button>
            </div>
            <div v-if="showTemplatePreview">
                <b-card class="no-hover">
                    <entry-fields
                        v-if="currentPreset.template"
                        :template="currentPreset.template"
                        :content="() => Object()"
                        :edit="true"
                        :readOnly="true"
                    />
                    <span v-else>
                        Select a template to preview
                    </span>
                </b-card>
            </div>
        </div>
        <div v-else-if="currentPreset.type === 'p'">
            <h2 class="theme-h2 field-heading required">
                Amount of points
                <tooltip
                    tip="The amount of points students should have achieved by the deadline of this node to be on
                    schedule, new entries can still be added until the assignment's lock date"
                />
            </h2>
            <b-input
                v-model="currentPreset.target"
                type="number"
                class="theme-input"
                placeholder="Amount of points"
                min="1"
                :max="assignmentDetails.points_possible"
            />
        </div>
        <b-button
            v-if="!newPreset"
            class="delete-button full-width mt-2"
            @click.prevent="emitDeletePreset"
        >
            <icon name="trash"/>
            Remove preset
        </b-button>
    </b-card>
</template>

<script>
import textEditor from '@/components/assets/TextEditor.vue'
import tooltip from '@/components/assets/Tooltip.vue'

export default {
    components: {
        tooltip,
        textEditor,
    },
    props: ['newPreset', 'currentPreset', 'templates', 'assignmentDetails'],
    data () {
        return {
            showTemplatePreview: false,
        }
    },
    computed: {
        // Ensure the unlock date is between the assignment unlock date and before preset due / lock date and
        // assignment due / lock date .
        unlockDateConfig () {
            const additionalConfig = {}

            if (this.currentPreset.due_date) {
                additionalConfig.maxDate = new Date(this.currentPreset.due_date)
            } else if (this.currentPreset.lock_date) {
                additionalConfig.maxDate = new Date(this.currentPreset.lock_date)
            } else if (this.assignmentDetails.lock_date) {
                additionalConfig.maxDate = new Date(this.assignmentDetails.lock_date)
            }

            // Assignment due date can be before the current preset lock date.
            if (this.assignmentDetails.due_date && (!additionalConfig.maxDate
                || new Date(this.assignmentDetails.due_date) < additionalConfig.maxDate)) {
                additionalConfig.maxDate = new Date(this.assignmentDetails.due_date)
            }

            if (this.assignmentDetails.unlock_date) {
                additionalConfig.minDate = new Date(this.assignmentDetails.unlock_date)
            }

            return Object.assign({}, additionalConfig, this.$root.flatPickrTimeConfig)
        },
        // Ensure the due date is preset unlock / lock date and between the assignment unlock and due / lock date.
        dueDateConfig () {
            const additionalConfig = {}

            if (this.currentPreset.unlock_date) {
                additionalConfig.minDate = new Date(this.currentPreset.unlock_date)
            } if (this.assignmentDetails.unlock_date) {
                additionalConfig.minDate = new Date(this.assignmentDetails.unlock_date)
            }

            if (this.currentPreset.lock_date) {
                additionalConfig.maxDate = new Date(this.currentPreset.lock_date)
            } else if (this.assignmentDetails.lock_date) {
                additionalConfig.maxDate = new Date(this.assignmentDetails.lock_date)
            }

            // Assignment due date can be before the current preset lock date.
            if (this.assignmentDetails.due_date && (!additionalConfig.maxDate
                || new Date(this.assignmentDetails.due_date) < additionalConfig.maxDate)) {
                additionalConfig.maxDate = new Date(this.assignmentDetails.due_date)
            }

            return Object.assign({}, additionalConfig, this.$root.flatPickrTimeConfig)
        },
        // Ensure the lock date is after the preset unlock / due date and betwween the assignment unlock / due and lock
        // date.
        lockDateConfig () {
            const additionalConfig = {}

            if (this.currentPreset.due_date) {
                additionalConfig.minDate = new Date(this.currentPreset.due_date)
            } else if (this.currentPreset.unlock_date) {
                additionalConfig.minDate = new Date(this.currentPreset.unlock_date)
            } else if (this.assignmentDetails.unlock_date) {
                additionalConfig.minDate = new Date(this.assignmentDetails.unlock_date)
            }

            if (this.assignmentDetails.lock_date) {
                additionalConfig.maxDate = new Date(this.assignmentDetails.lock_date)
            }

            return Object.assign({}, additionalConfig, this.$root.flatPickrTimeConfig)
        },
        // Ensure the progress date is between the assignment unlock and due / lock date.
        progressDateConfig () {
            const additionalConfig = {}

            if (this.assignmentDetails.unlock_date) {
                additionalConfig.minDate = new Date(this.assignmentDetails.unlock_date)
            }

            if (this.assignmentDetails.due_date) {
                additionalConfig.maxDate = new Date(this.assignmentDetails.due_date)
            } else if (this.assignmentDetails.lock_date) {
                additionalConfig.maxDate = new Date(this.assignmentDetails.lock_date)
            }

            return Object.assign({}, additionalConfig, this.$root.flatPickrTimeConfig)
        },
    },
    methods: {
        emitDeletePreset () {
            if (window.confirm('Are you sure you want to remove this preset from this format?')) {
                this.$emit('delete-preset')
            }
        },
    },
}
</script>
