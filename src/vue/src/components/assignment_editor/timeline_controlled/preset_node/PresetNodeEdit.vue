<template>
    <div>
        <preset-node-type-selection
            v-if="!edit"
            :presetNode="presetNode"
        />

        <b-card
            v-if="presetNode.type"
            class="overflow-x-hidden"
        >
            <template
                v-if="edit"
                #header
            >
                <b-button
                    class="red-button float-right"
                    @click="cancelPresetNodeEdit({ presetNode }); setModeToRead()"
                >
                    <icon name="ban"/>
                    Cancel
                </b-button>
                <h2 class="theme-h2">
                    {{ presetNode.display_name }}
                </h2>
            </template>

            <b-form-group
                label="Display name"
                class="required"
                :invalid-feedback="displayNameInvalidFeedback"
                :state="displayNameInputState"
            >
                <b-input
                    v-model="presetNode.display_name"
                    placeholder="Timeline display name"
                    trim
                    required
                />

                <small
                    v-if="presetNode.template && presetNode.template.allow_custom_title"
                >
                    The template setting <i>"allow custom title"</i> allows students to override this value.
                </small>
            </b-form-group>

            <preset-node-edit-select-and-preview-template
                v-if="presetNode.type === 'd'"
                :presetNode="presetNode"
            />

            <b-form-group
                v-else-if="presetNode.type === 'p'"
                class="required"
                :invalid-feedback="targetInvalidFeedback"
                :state="targetInputState"
            >
                <template #label>
                    Number of points
                    <tooltip
                        tip="The number of points students should have achieved by the deadline of this node to be on
                        schedule, new entries can still be added until the assignment's lock date"
                    />
                </template>

                <b-input
                    v-model="presetNode.target"
                    type="number"
                    placeholder="Number of points"
                    min="1"
                    required
                    :max="assignment.points_possible"
                />
            </b-form-group>

            <b-form-group label="Description">
                <text-editor
                    :id="`preset-description-${edit ? presetNode.id : presetNode.type}`"
                    :key="`preset-description-${edit ? presetNode.id : presetNode.type}`"
                    v-model="presetNode.description"
                    placeholder="Description"
                    footer="false"
                />
            </b-form-group>

            <preset-node-edit-dates
                ref="presetNodeDates"
                :presetNode="presetNode"
            />

            <b-form-group>
                <template
                    #label
                >
                    Files
                </template>

                <files-list
                    :attachNew="true"
                    :files="presetNode.attached_files"
                    @uploading-file="uploadingFiles ++"
                    @fileUploadSuccess="presetNode.attached_files.push($event) && uploadingFiles --"
                    @fileUploadFailed="uploadingFiles --"
                    @fileRemoved="(i) => presetNode.attached_files.splice(i, 1)"
                />
            </b-form-group>

            <template #footer>
                <b-button
                    class="green-button float-right"
                    @click.stop="finalizePresetNodeChanges()"
                >
                    <icon :name="(edit) ? 'save' : 'plus'"/>
                    {{ (edit) ? 'Save' : 'Add Deadline' }}
                </b-button>
            </template>
        </b-card>
    </div>
</template>

<script>
import PresetNodeEditDates from '@/components/assignment_editor/timeline_controlled/preset_node/PresetNodeEditDates.vue'
import PresetNodeEditSelectAndPreviewTemplate from
    '@/components/assignment_editor/timeline_controlled/preset_node/PresetNodeEditSelectAndPreviewTemplate.vue'
import PresetNodeTypeSelection from
    '@/components/assignment_editor/timeline_controlled/preset_node/PresetNodeTypeSelection.vue'
import Tooltip from '@/components/assets/Tooltip.vue'
import filesList from '@/components/assets/file_handling/FilesList.vue'

import { mapActions, mapGetters, mapMutations } from 'vuex'

export default {
    components: {
        TextEditor: () => import(/* webpackChunkName: 'text-editor' */ '@/components/assets/TextEditor.vue'),
        PresetNodeEditDates,
        PresetNodeEditSelectAndPreviewTemplate,
        PresetNodeTypeSelection,
        Tooltip,
        filesList,
    },
    data () {
        return {
            showTemplatePreview: false,
            displayNameInputState: null,
            displayNameInvalidFeedback: null,
            targetInputState: null,
            targetInvalidFeedback: null,
            validDates: null,
            uploadingFiles: 0,
            conflictingPreset: null,
        }
    },
    computed: {
        ...mapGetters({
            assignment: 'assignment/assignment',
            presetNode: 'assignmentEditor/selectedPresetNode',
            presetNodes: 'presetNode/assignmentPresetNodes',
            templates: 'template/assignmentTemplates',
        }),
        edit () {
            return this.presetNode.id >= 0
        },
        targetAndDueDate () {
            return this.presetNode.target, this.presetNode.due_date, Date.now() // eslint-disable-line
        },
    },
    watch: {
        'presetNode.display_name': 'validateDisplayNameInput',
        targetAndDueDate: 'validateTargetAndDueDateInput',
    },
    methods: {
        ...mapActions({
            create: 'presetNode/create',
            update: 'presetNode/update',
            cancelPresetNodeEdit: 'assignmentEditor/cancelPresetNodeEdit',
            presetNodeCreated: 'assignmentEditor/presetNodeCreated',
            presetNodeUpdated: 'assignmentEditor/presetNodeUpdated',
        }),
        ...mapMutations({
            setModeToRead: 'assignmentEditor/SET_ACTIVE_COMPONENT_MODE_TO_READ',
        }),
        earlier_progress_goal_with_higher_target () {
            return (
                this.presetNode.type === 'p'
                && this.presetNode.due_date
                && this.presetNode.target
                && this.presetNodes.some((elem) => { // eslint-disable-line
                    this.conflictingPreset = elem

                    return (
                        elem.id !== this.presetNode.id
                        && elem.type === 'p'
                        && elem.target > this.presetNode.target
                        && Date.parse(elem.due_date) < Date.parse(this.presetNode.due_date)
                    )
                })
            )
        },
        later_progress_goal_with_lower_target () {
            return (
                this.presetNode.type === 'p'
                && this.presetNode.due_date
                && this.presetNode.target
                && this.presetNodes.some((elem) => { // eslint-disable-line
                    this.conflictingPreset = elem

                    return (
                        elem.id !== this.presetNode.id
                        && elem.type === 'p'
                        && elem.target < this.presetNode.target
                        && Date.parse(elem.due_date) > Date.parse(this.presetNode.due_date)
                    )
                })
            )
        },
        validateDisplayNameInput () {
            const displayName = this.presetNode.display_name

            if (displayName === '') {
                this.displayNameInputState = false
                this.displayNameInvalidFeedback = 'Display name cannot be empty.'
            } else {
                this.displayNameInputState = null
            }
        },
        validateTargetAndDueDateInput () {
            if (this.presetNode.target < 0) {
                this.targetInputState = false
                this.targetInvalidFeedback = 'Number of points should be a positive number.'
            } else if (this.presetNode.target > this.assignment.points_possible) {
                this.targetInputState = false
                this.targetInvalidFeedback = `
                    Number of points exceeds the maximum number of points of the assignment.
                `
            } else if (this.presetNode.target === '') {
                this.targetInputState = false
                this.targetInvalidFeedback = 'Number of points is required.'
            } else if (this.earlier_progress_goal_with_higher_target()) {
                this.targetInputState = false
                this.targetInvalidFeedback = `
                    Deadline "${this.conflictingPreset.display_name}" is due earlier with a higher number
                    of points (${this.conflictingPreset.target}).
                `
            } else if (this.later_progress_goal_with_lower_target()) {
                this.targetInputState = false
                this.targetInvalidFeedback = `
                    Deadline "${this.conflictingPreset.display_name}" is due later with a lower number
                    of points (${this.conflictingPreset.target}).
                `
            } else {
                this.targetInputState = null
            }
        },
        finalizePresetNodeChanges () {
            if (!this.validateData() || !this.$refs.presetNodeDates.validateData()) { return }

            if (this.edit) {
                this.update({ data: this.presetNode, aID: this.$route.params.aID })
                    .then((presetNode) => { this.presetNodeUpdated({ presetNode }) })
            } else {
                this.create({ data: this.presetNode, aID: this.$route.params.aID })
                    .then((createdPresetNode) => {
                        this.presetNodeCreated({ presetNode: createdPresetNode })
                    })
            }
        },
    },
}
</script>
