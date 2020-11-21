<template>
    <b-modal
        :id="modalID"
        :ref="modalID"
        size="lg"
        title="Import template"
        hideFooter
        noEnforceFocus
    >
        <b-card class="no-hover">
            <div v-if="importableTemplates && importableTemplates.length > 0">
                <h2 class="theme-h2 multi-form">
                    Select a template to import
                </h2>
                <p>
                    This action will create a new template in the current assignment that is identical to the template
                    of your choice. Any changes made will only affect the current assignment.
                </p>

                <theme-select
                    v-model="selectedCourse"
                    label="name"
                    trackBy="id"
                    :options="courses"
                    :multiple="false"
                    :searchable="true"
                    placeholder="Select A Course"
                    class="multi-form"
                    @select="() => {
                        selectedAssignment = null
                        selectedTemplate = null
                        previewTemplate = false
                        templates = []
                    }"
                />
                <theme-select
                    v-if="selectedCourse"
                    v-model="selectedAssignment"
                    label="name"
                    trackBy="id"
                    :options="assignments"
                    :multiple="false"
                    :searchable="true"
                    placeholder="Select An Assignment"
                    class="multi-form"
                    @select="() => {
                        selectedTemplate = null
                        previewTemplate = false
                        templates = []
                    }"
                    @input="getTemplatesForSelectedAssignment"
                />
                <theme-select
                    v-if="selectedAssignment"
                    v-model="selectedTemplate"
                    label="name"
                    trackBy="id"
                    :options="templates"
                    :multiple="false"
                    :searchable="true"
                    placeholder="Select A Template"
                    class="multi-form"
                    @select="() => {
                        if (previewTemplate) {
                            previewTemplate = null
                        }
                    }"
                />

                <hr/>

                <b-card
                    v-if="previewTemplate"
                    class="no-hover multi-form"
                >
                    <entry-fields
                        :template="selectedTemplate"
                        :content="() => Object()"
                        :edit="true"
                        :readOnly="true"
                    />
                </b-card>

                <b-button
                    v-if="!previewTemplate"
                    class="green-button"
                    :class="{ 'input-disabled': !selectedTemplate }"
                    @click="previewTemplate = true"
                >
                    <icon name="eye"/>
                    Show preview
                </b-button>
                <b-button
                    v-else
                    class="red-button"
                    @click="previewTemplate = false"
                >
                    <icon name="eye-slash"/>
                    Hide preview
                </b-button>

                <b-button
                    class="orange-button float-right"
                    :class="{ 'input-disabled': !selectedTemplate }"
                    @click="importTemplate(selectedTemplate)"
                >
                    <icon name="file-import"/>
                    Import template
                </b-button>
            </div>

            <div v-else>
                <b>No existing templates available</b>
                <hr class="m-0 mb-1"/>
                Only templates in assignments where you have permission to edit are available to import.
            </div>
        </b-card>
    </b-modal>
</template>

<script>
import EntryFields from '@/components/entry/EntryFields.vue'

import assignmentAPI from '@/api/assignment.js'
import utils from '@/utils/generic_utils.js'

export default {
    components: {
        EntryFields,
    },
    props: {
        modalID: {
            required: true,
        },
        aID: {
            required: true,
        },
    },
    data () {
        return {
            selectedCourse: null,
            selectedAssignment: null,
            selectedTemplate: null,
            previewTemplate: null,
            importableTemplates: [],

            // The actual templates (so containing fields, description etc.) which can be selected.
            templates: [],
        }
    },
    computed: {
        courses () {
            return this.importableTemplates.map((importable) => {
                const course = { ...importable.course }
                course.name = utils.courseWithDatesDisplay(course)
                return course
            })
        },
        assignments () {
            return this.importableTemplates.find(importable => importable.course.id === this.selectedCourse.id)
                .assignments
        },
    },
    created () {
        assignmentAPI.getImportable()
            .then((data) => {
                data.forEach((d) => {
                    d.assignments = d.assignments.filter(assignment => assignment.id !== this.aID)
                })
                this.importableTemplates = data.filter(d => d.assignments.length > 0)
            })
    },
    methods: {
        importTemplate (template) {
            this.$emit('imported-template', template)
            this.$refs[this.modalID].hide()
            this.selectedCourse = null
            this.selectedAssignment = null
            this.selectedTemplate = null
            this.previewTemplate = false
        },
        getTemplatesForSelectedAssignment () {
            assignmentAPI.getTemplates(this.selectedAssignment.id)
                .then((templates) => {
                    this.templates = templates
                })
                .catch(() => {
                    this.$toasted.error('Something went wrong while loading templates to import.')
                })
        },
    },
}
</script>
