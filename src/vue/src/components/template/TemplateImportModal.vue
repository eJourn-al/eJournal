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
                        previewTemplate = null
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
                        previewTemplate = null
                    }"
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
                        :template="previewTemplate"
                        :content="() => Object()"
                        :edit="true"
                        :readOnly="true"
                    />
                </b-card>

                <b-button
                    v-if="!previewTemplate"
                    class="add-button"
                    :class="{ 'input-disabled': !selectedTemplate }"
                    @click="showTemplatePreview"
                >
                    <icon name="eye"/>
                    Show preview
                </b-button>
                <b-button
                    v-else
                    class="delete-button"
                    @click="previewTemplate = null"
                >
                    <icon name="eye-slash"/>
                    Hide preview
                </b-button>

                <b-button
                    class="change-button float-right"
                    :class="{ 'input-disabled': !selectedTemplate }"
                    @click="importTemplate(selectedTemplate.id)"
                >
                    <icon name="file-import"/>
                    Import template
                </b-button>
            </div>

            <div v-else>
                <h4 class="theme-h4">
                    No existing templates available
                </h4>
                <hr class="m-0 mb-1"/>
                Only templates in assignments where you have permission to edit are available to import.
            </div>
        </b-card>
    </b-modal>
</template>

<script>
import assignmentAPI from '@/api/assignment.js'

export default {
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
        }
    },
    computed: {
        courses () {
            return this.importableTemplates.map((importable) => {
                const course = { ...importable.course }
                if (course.startdate || course.enddate) {
                    course.name += ` (${course.startdate ? course.startdate.substring(0, 4) : ''} - ${
                        course.enddate ? course.enddate.substring(0, 4) : ''})`
                }

                return course
            })
        },
        assignments () {
            return this.importableTemplates.find(importable => importable.course.id === this.selectedCourse.id)
                .assignments
        },
        templates () {
            return this.selectedAssignment.templates
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
        showTemplatePreview () {
            assignmentAPI.importTemplate(this.aID, { template_id: this.selectedTemplate.id }).then((template) => {
                this.previewTemplate = template
            })
        },
        importTemplate () {
            assignmentAPI.importTemplate(this.aID, { template_id: this.selectedTemplate.id }).then((template) => {
                this.$emit('imported-template', template)
                this.$refs[this.modalID].hide()
                this.selectedCourse = null
                this.selectedAssignment = null
                this.selectedTemplate = null
                this.previewTemplate = null
            })
        },
    },
}
</script>
