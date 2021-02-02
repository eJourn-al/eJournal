<template>
    <div>
        <preset-node-type-selection
            v-if="!edit"
            :presetNode="presetNode"
        />

        <b-card
            v-if="presetNode.type"
            :class="$root.getBorderClass($route.params.cID)"
            class="no-hover overflow-x-hidden"
        >
            <b-row
                v-if="edit"
                no-gutters
                class="multi-form"
            >
                <span class="theme-h2">
                    {{ presetNode.display_name }}
                </span>

                <b-button
                    class="red-button ml-auto"
                    @click="cancelPresetNodeEdit({ presetNode }); setModeToRead()"
                >
                    <icon name="ban"/>
                    Cancel
                </b-button>
            </b-row>

            <b-form-group
                label="Display name"
                class="required"
                :invalid-feedback="displayNameInvalidFeedback"
                :state="displayNameInputState"
            >
                <b-input
                    v-model="presetNode.display_name"
                    class="theme-input"
                    placeholder="Timeline display name"
                    trim
                    required
                />
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
                    class="theme-input"
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
                    class="multi-form"
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

            <hr/>

            <b-row no-gutters>
                <b-button
                    v-if="edit"
                    class="red-button"
                    @click.stop="deletePresetNode()"
                >
                    <icon name="trash"/>
                    Delete
                </b-button>

                <b-button
                    class="green-button ml-auto"
                    @click.stop="finalizePresetNodeChanges()"
                >
                    <icon :name="(edit) ? 'save' : 'plus'"/>
                    <!-- QUESTION: User facing it might make more sense to use 'deadline' over 'preset'? -->
                    {{ (edit) ? 'Save' : 'Add Preset' }}
                </b-button>
            </b-row>
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
        'presetNode.display_name': {
            handler (displayName) {
                if (displayName === '') {
                    this.displayNameInputState = false
                    this.displayNameInvalidFeedback = 'Display name cannot be empty.'
                } else {
                    this.displayNameInputState = null
                }
            },
        },
        targetAndDueDate: {
            handler () {
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
        },
    },
    methods: {
        ...mapActions({
            create: 'presetNode/create',
            delete: 'presetNode/delete',
            update: 'presetNode/update',
            cancelPresetNodeEdit: 'assignmentEditor/cancelPresetNodeEdit',
            presetNodeCreated: 'assignmentEditor/presetNodeCreated',
            presetNodeDeleted: 'assignmentEditor/presetNodeDeleted',
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
        deletePresetNode () {
            if (window.confirm(
                `Are you sure you want to remove '${this.presetNode.display_name}' from the assignment?`)) {
                this.delete({ id: this.presetNode.id, aID: this.$route.params.aID })
                    .then(() => { this.presetNodeDeleted({ presetNode: this.presetNode }) })
            }
        },
        finalizePresetNodeChanges () {
            if (!this.validateData() || !this.$refs.presetNodeDates.validateData()) { return }

            if (this.edit) {
                this.update({ data: this.presetNode, aID: this.$route.params.aID })
                    .then(() => { this.presetNodeUpdated({ presetNode: this.presetNode }) })
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
