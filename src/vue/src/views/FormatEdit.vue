<!--
    Format Editor view.
    Lists all templates used within the assignment.
    Template availability for adding by the student can be toggled on a per-template basis.
    Presets are given in a list format, same as the journal view.
-->

<template>
    <b-row
        class="outer-container-timeline-page"
        noGutters
    >
        <b-col
            md="12"
            lg="8"
            xl="9"
            class="inner-container-timeline-page"
        >
            <b-col
                md="12"
                lg="auto"
                xl="4"
                class="left-content-timeline-page"
            >
                <bread-crumb
                    v-if="$root.lgMax"
                    v-intro="'Welcome to the assignment editor!<br/>This is where you can configure the structure of \
                    your assignment. Proceed with this tutorial to learn more.'"
                    v-intro-step="1"
                >
                    <icon
                        v-intro="'That\'s it! If you have any more questions, do not hesitate to contact us via the \
                        support button at the bottom of any page. This tutorial can be consulted again by clicking \
                        the info sign.'"
                        v-intro-step="4"
                        v-b-tooltip:hover="'Click to start a tutorial for this page'"
                        name="info-circle"
                        scale="1.5"
                        class="info-icon shift-up-5 ml-1"
                        @click.native="startTour"
                    />
                </bread-crumb>
                <timeline
                    v-intro="'The timeline forms the basis for an assignment. The name, due date and other details \
                    of the assignment can also be changed here, by clicking the first node.<br/><br/>The timeline \
                    contains a node for every entry. You can add two different types of nodes to it:<br/><br/><ul> \
                    <li><b>Preset entries</b> are entries with a specific template which have to be completed before \
                    a set deadline</li><li><b>Progress goals</b> are point targets that have to be met before a \
                    set deadline</li></ul>New nodes can be added via the \'+\' node. Click any node to view its \
                    contents.'"
                    v-intro-step="3"
                    :selected="currentNode"
                    :nodes="presets"
                    :assignment="assignmentDetails"
                    :edit="true"
                    @select-node="(node) => {
                        currentNode = node
                    }"
                />
            </b-col>

            <b-col
                md="12"
                lg="auto"
                xl="8"
                class="main-content-timeline-page"
            >
                <bread-crumb
                    v-if="$root.xl"
                    v-intro="'Welcome to the assignment editor!<br/>This is where you can configure the structure of \
                    your assignment. Proceed with this tutorial to learn more.'"
                    v-intro-step="1"
                >
                    <icon
                        v-intro="'That\'s it! If you have any more questions, do not hesitate to contact us via the \
                        support button at the bottom of any page. This tutorial can be consulted again by clicking \
                        the info sign.'"
                        v-intro-step="4"
                        v-b-tooltip:hover="'Click to start a tutorial for this page'"
                        name="info-circle"
                        scale="1.75"
                        class="info-icon shift-up-5 ml-1"
                        @click.native="startTour"
                    />
                </bread-crumb>

                <div v-if="currentNode === -1">
                    <b-card
                        :class="$root.getBorderClass($route.params.cID)"
                        class="no-hover"
                    >
                        <assignment-details
                            ref="assignmentDetails"
                            :class="{ 'input-disabled' : saveRequestInFlight }"
                            :assignmentDetails="assignmentDetails"
                            :presetNodes="presets"
                        />
                    </b-card>
                    <!-- TODO: Re-enable after UI changes. -->
                    <!-- <b-card
                        v-if="$hasPermission('can_delete_assignment')"
                        class="no-hover border-red"
                    >
                        <b-button
                            :class="{
                                'input-disabled': assignmentDetails.lti_count > 1 && assignmentDetails.active_lti_course
                                    && parseInt(assignmentDetails.active_lti_course.cID) ===
                                        parseInt($route.params.cID)}"
                            class="red-button full-width"
                            @click="deleteAssignment"
                        >
                            <icon name="trash"/>
                            {{ assignmentDetails.course_count > 1 ? 'Remove' : 'Delete' }} assignment
                        </b-button>
                    </b-card> -->
                </div>

                <preset-node-card
                    v-else-if="presets.length > 0 && currentNode !== -1 && currentNode < presets.length"
                    :key="`preset-node-${currentNode}`"
                    :class="{ 'input-disabled' : saveRequestInFlight }"
                    :currentPreset="presets[currentNode]"
                    :templates="templates"
                    :assignmentDetails="assignmentDetails"
                    @delete-preset="deletePreset"
                    @change-due-date="sortPresets"
                    @new-template="newTemplateInPreset"
                />

                <add-preset-node
                    v-else-if="currentNode === presets.length"
                    :class="{ 'input-disabled' : saveRequestInFlight }"
                    :templates="templates"
                    :assignmentDetails="assignmentDetails"
                    @add-preset="addPreset"
                    @new-template="newTemplateInPreset"
                />

                <b-card
                    v-else-if="currentNode === presets.length + 1"
                    class="no-hover"
                    :class="$root.getBorderClass($route.params.cID)"
                >
                    <h2 class="theme-h2">
                        End of assignment
                    </h2>
                    <p>This is the end of the assignment.</p>
                </b-card>

                <b-modal
                    ref="templateModal"
                    size="lg"
                    title="Edit template"
                    hideFooter
                    noEnforceFocus
                >
                    <template-editor
                        v-if="currentTemplate !== -1"
                        :template="templates[currentTemplate]"
                    />
                </b-modal>

                <template-import-modal
                    modalID="import-template-modal"
                    :aID="aID"
                    @imported-template="importTemplate"
                />
            </b-col>
        </b-col>

        <b-col
            md="12"
            lg="4"
            xl="3"
            class="right-content-timeline-page right-content"
        >
            <h3 class="theme-h3">
                Entry Templates
            </h3>
            <div
                v-intro="'Every assignment contains customizable <i>templates</i> which specify what the contents of \
                each journal entry should be. There are two different types of templates:<br/><br/><ul><li><b>\
                Unlimited templates</b> can be freely used by students as often as they want</li><li><b>Preset-only \
                templates</b> can be used only for preset entries that you add to the timeline</li></ul>You can \
                preview and edit a template by clicking on it.'"
                v-intro-step="2"
                :class="{ 'input-disabled' : saveRequestInFlight }"
                class="d-block"
            >
                <b-card
                    :class="$root.getBorderClass($route.params.cID)"
                    class="no-hover"
                >
                    <div
                        v-if="templates.length > 0"
                        class="template-list-header"
                    >
                        <b class="float-right">
                            Type
                        </b>
                        <b>Name</b>
                    </div>
                    <template-link
                        v-for="(template, index) in templates"
                        :key="template.id"
                        :template="template"
                        @edit-template="showTemplateModal(index)"
                        @delete-template="deleteTemplate(index)"
                    />
                    <b-button
                        class="green-button mt-2 full-width"
                        @click="newTemplate()"
                    >
                        <icon name="plus"/>
                        Create New Template
                    </b-button>
                    <b-button
                        v-b-modal="'import-template-modal'"
                        class="orange-button mt-2 full-width"
                    >
                        <icon name="file-import"/>
                        Import Template
                    </b-button>
                </b-card>
            </div>

            <h3 class="theme-h3">
                Actions
            </h3>
            <manage-assignment-categories
                :templates="templates"
            />
        </b-col>

        <b-button
            v-if="isChanged"
            :class="{ 'input-disabled' : saveRequestInFlight }"
            class="green-button fab"
            @click.prevent.stop="saveFormat"
        >
            <icon
                name="save"
                scale="1.5"
            />
        </b-button>
    </b-row>
</template>

<script>
import ManageAssignmentCategories from '@/components/format/ManageAssignmentCategories.vue'
import assignmentDetails from '@/components/assignment/AssignmentDetails.vue'
import breadCrumb from '@/components/assets/BreadCrumb.vue'
import formatAddPresetNode from '@/components/format/FormatAddPresetNode.vue'
import formatPresetNodeCard from '@/components/format/FormatPresetNodeCard.vue'
import formatTemplateLink from '@/components/format/FormatTemplateLink.vue'
import templateEdit from '@/components/template/TemplateEdit.vue'
import templateImportModal from '@/components/template/TemplateImportModal.vue'
import timeline from '@/components/timeline/Timeline.vue'

import assignmentAPI from '@/api/assignment.js'
import formatAPI from '@/api/format.js'

export default {
    name: 'FormatEdit',
    components: {
        breadCrumb,
        'assignment-details': assignmentDetails,
        'template-link': formatTemplateLink,
        'preset-node-card': formatPresetNodeCard,
        'add-preset-node': formatAddPresetNode,
        'template-editor': templateEdit,
        templateImportModal,
        timeline,
        ManageAssignmentCategories,
    },
    props: ['cID', 'aID'],
    data () {
        return {
            assignmentDetails: {},

            currentNode: -1,

            templates: [],
            deletedTemplates: [],

            presets: [],
            deletedPresets: [],
            newPresetId: -1,

            originalData: '{}',
            currentData: {},
            saveRequestInFlight: false,

            currentTemplate: -1,
            newTemplateId: -1,
        }
    },
    computed: {
        isChanged () {
            return !this.saveRequestInFlight && JSON.stringify(this.currentData, this.replacer) !== this.originalData
        },
    },
    created () {
        this.loadFormat()

        window.addEventListener('beforeunload', (e) => { // eslint-disable-line
            if (this.$route.name === 'FormatEdit' && this.isChanged) {
                const dialogText = 'Unsaved changes will be lost if you leave. Do you wish to continue?'
                e.returnValue = dialogText
                return dialogText
            }
        })
    },
    methods: {
        loadFormat () {
            formatAPI.get(this.aID, this.cID)
                .then((data) => {
                    this.currentData = data
                    this.originalData = JSON.stringify(data, this.replacer)
                    this.assignmentDetails = data.assignment_details
                    this.templates = data.format.templates
                    this.presets = data.format.presets
                    this.deletedTemplates = []
                    this.deletedPresets = []
                    this.currentTemplate = -1
                    this.newTemplateId = -1
                    this.newPresetId = -1

                    if (this.$store.getters['preferences/saved'].show_format_tutorial) {
                        this.$store.commit('preferences/CHANGE_PREFERENCES', { show_format_tutorial: false })
                        this.startTour()
                    }
                })
        },
        checkDateOrder (first, second) {
            // Returns false if order is incorrect
            return !first || !second || Date.parse(first) <= Date.parse(second)
        },
        checkValidDate (date) {
            // Returns false if date is not valid
            return date == null || !Number.isNaN(Date.parse(date))
        },
        // eslint-disable-next-line max-lines-per-function
        saveFormat () {
            let lastTarget = 0
            const templatesIds = []

            const presetErrors = [
                {
                    check: preset => this.checkDateOrder(this.assignmentDetails.unlock_date, preset.unlock_date),
                    message: 'One or more presets have an unlock date before the assignment unlock date.',
                    occurred: false,
                },
                {
                    check: preset => this.checkDateOrder(preset.unlock_date, this.assignmentDetails.due_date),
                    message: 'One or more presets have an unlock date after the assignment due date.',
                    occurred: false,
                },
                {
                    check: preset => this.checkDateOrder(this.assignmentDetails.unlock_date, preset.due_date),
                    message: 'One or more presets have a due date before the assignment unlock date.',
                    occurred: false,
                },
                {
                    check: preset => this.checkDateOrder(preset.due_date, this.assignmentDetails.due_date),
                    message: 'One or more presets have a due date after the assignment due date.',
                    occurred: false,
                },
                {
                    check: preset => this.checkDateOrder(this.assignmentDetails.unlock_date, preset.lock_date),
                    message: 'One or more presets have a lock date before the assignment unlock date.',
                    occurred: false,
                },
                {
                    check: preset => this.checkDateOrder(preset.lock_date, this.assignmentDetails.lock_date),
                    message: 'One or more presets have a lock date after the assignment lock date.',
                    occurred: false,
                },
                {
                    check: preset => this.checkDateOrder(preset.unlock_date, preset.due_date),
                    message: 'One or more presets are due before their unlock date.',
                    occurred: false,
                },
                {
                    check: preset => this.checkDateOrder(preset.due_date, preset.lock_date),
                    message: 'One or more presets are lock before their due date.',
                    occurred: false,
                },
                {
                    check: preset => this.checkValidDate(preset.unlock_date),
                    message: 'One or more presets have an invalid unlock date.',
                    occurred: false,
                },
                {
                    check: preset => this.checkValidDate(preset.due_date),
                    message: 'One or more presets have an invalid due date.',
                    occurred: false,
                },
                {
                    check: preset => this.checkValidDate(preset.lock_date),
                    message: 'One or more presets have an invalid lock date.',
                    occurred: false,
                },
                {
                    check: preset => !(preset.type === 'd' && (
                        typeof preset.template.id === 'undefined' || !templatesIds.includes(preset.template.id))),
                    message: 'One or more presets have an invalid template.',
                    occurred: false,
                },
                {
                    check: preset => !(preset.type === 'p' && Number.isNaN(parseFloat(preset.target, 10))),
                    message: 'One or more presets have an invalid target.',
                    occurred: false,
                },
                {
                    check: (preset) => {
                        if (preset.type !== 'p') {
                            return true
                        }
                        const inOrder = lastTarget < preset.target
                        lastTarget = preset.target
                        return inOrder
                    },
                    message: 'One or more preset targets are out of order.',
                    occurred: false,
                },
                {
                    check: preset => preset.target <= this.assignmentDetails.points_possible,
                    message: 'Preset target is higher than the maximum possible points for the assignment.',
                    occurred: false,
                },
            ]
            let untitledTemplates = false
            this.templates.forEach((template) => {
                templatesIds.push(template.id)
                if (!untitledTemplates && !template.name) {
                    untitledTemplates = true
                    this.$toasted.error('One or more templates are untitled. Please check the templates and try'
                    + ' again.')
                }
            })

            let invalidAssignmentDetails = false
            if (this.$refs.assignmentDetails && !this.$refs.assignmentDetails.validateDetails()) {
                invalidAssignmentDetails = true
            }

            presetErrors.forEach((error) => {
                error.occurred = false
            })
            this.presets.forEach((preset) => {
                presetErrors.forEach((error) => {
                    error.occurred = error.occurred || !error.check(preset)
                })
            })

            let hasError = false
            presetErrors.forEach((error) => {
                if (error.occurred) {
                    this.$toasted.error(error.message)
                    hasError = true
                }
            })

            if (untitledTemplates || invalidAssignmentDetails || hasError) {
                return
            }

            this.saveRequestInFlight = true
            formatAPI.update(this.aID, {
                assignment_details: this.assignmentDetails,
                templates: this.templates,
                presets: this.presets,
                removed_templates: this.deletedTemplates,
                removed_presets: this.deletedPresets,
                course_id: this.cID,
            }, { customSuccessToast: 'New format saved' })
                .then((data) => {
                    this.currentData = data
                    this.originalData = JSON.stringify(data, this.replacer)
                    this.assignmentDetails = data.assignment_details
                    this.templates = data.format.templates
                    this.presets = data.format.presets
                    this.deletedTemplates = []
                    this.deletedPresets = []
                    this.saveRequestInFlight = false
                    this.currentTemplate = -1
                    this.newTemplateId = -1
                    this.newPresetId = -1
                    this.currentNode = -1
                })
                .catch(() => { this.saveRequestInFlight = false })
        },
        addPreset (preset) {
            preset.id = this.newPresetId--
            this.presets.push(preset)
            this.currentNode = this.presets.indexOf(preset)
            this.sortPresets()
        },
        deletePreset () {
            if (typeof this.presets[this.currentNode].id !== 'undefined') {
                this.deletedPresets.push(this.presets[this.currentNode])
            }
            this.presets.splice(this.currentNode, 1)
            this.currentNode = Math.min(this.currentNode, this.presets.length - 1)
        },
        sortPresets () {
            if (this.currentNode > 0 && this.currentNode < this.presets.length) {
                const currentPreset = this.presets[this.currentNode]
                this.presets.sort((a, b) => new Date(a.due_date) - new Date(b.due_date))
                this.currentNode = this.presets.indexOf(currentPreset)
            } else {
                this.presets.sort((a, b) => new Date(a.due_date) - new Date(b.due_date))
            }
        },
        newTemplate () {
            const template = {
                field_set: [{
                    type: 'rt',
                    title: 'Content',
                    description: '',
                    options: null,
                    location: 0,
                    required: true,
                }],
                name: 'Entry',
                id: this.newTemplateId--,
                preset_only: false,
            }
            this.templates.push(template)
            this.showTemplateModal(this.templates.length - 1)
            return template
        },
        newTemplateInPreset (preset) {
            const template = this.newTemplate()
            template.preset_only = true
            preset.template = template
        },
        importTemplate (template) {
            template.id = this.newTemplateId--
            this.templates.push(template)
        },
        deleteTemplate (index) {
            if (this.templates[index].id > 0) {
                this.deletedTemplates.push(this.templates[index])
            }
            this.templates.splice(index, 1)
            this.currentTemplate = -1
        },
        showTemplateModal (index) {
            this.currentTemplate = index
            this.$refs.templateModal.show()
        },
        startTour () {
            this.$intro().start()
        },
        replacer (name, value) {
            if (value === null) {
                return ''
            }
            return value
        },
        editJournals () {
            alert('Not implemented yet')
        },
        deleteAssignment () {
            if (this.assignmentDetails.course_count > 1
                ? window.confirm('Are you sure you want to remove this assignment from the course?')
                : window.confirm('Are you sure you want to delete this assignment?')) {
                assignmentAPI.delete(
                    this.assignmentDetails.id,
                    this.$route.params.cID,
                    {
                        customSuccessToast: this.assignmentDetails.course_count > 1
                            ? 'Removed assignment' : 'Deleted assignment',
                    },
                )
                    .then(() => this.$router.push({
                        name: 'Course',
                        params: {
                            cID: this.$route.params.cID,
                        },
                    }))
            }
        },
    },
    beforeRouteLeave (to, from, next) {
        if (this.isChanged && !window.confirm('Unsaved changes will be lost if you leave. Do you wish to continue?')) {
            next(false)
            return
        }

        this.$intro().exit()
        next()
    },
}
</script>

<style lang="sass">
@import '~sass/partials/timeline-page-layout.sass'

.template-list-header
    border-bottom: 2px solid $theme-dark-grey
</style>
