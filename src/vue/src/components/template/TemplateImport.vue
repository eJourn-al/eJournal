<template>
    <load-wrapper :loading="loading">
        <b-card>
            <h2
                slot="header"
                class="theme-h2 mb-2"
            >
                Import template
            </h2>
            <template v-if="importableTemplates && importableTemplates.length > 0">
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
                    class="mb-2"
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
                    class="mb-2"
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
                    class="mb-2"
                    @select="() => {
                        if (previewTemplate) {
                            previewTemplate = null
                        }
                    }"
                />

                <div
                    v-if="previewTemplate"
                    class="p-2"
                >
                    <entry-preview
                        class="mb-2"
                        :template="selectedTemplate"
                    />
                </div>
            </template>

            <not-found
                v-else
                subject="templates"
                explanation="Only templates in assignments where you have permission to edit are available to import."
            />

            <template
                v-if="importableTemplates && importableTemplates.length > 0"
                #footer
            >
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
                    class="green-button float-right"
                    :class="{ 'input-disabled': !selectedTemplate }"
                    @click="importTemplate(selectedTemplate)"
                >
                    <icon name="plus"/>
                    Add template
                </b-button>
            </template>
        </b-card>
    </load-wrapper>
</template>

<script>
import EntryPreview from '@/components/entry/EntryPreview.vue'
import LoadWrapper from '@/components/loading/LoadWrapper.vue'

import assignmentAPI from '@/api/assignment.js'
import utils from '@/utils/generic_utils.js'

import { mapActions, mapMutations } from 'vuex'

export default {
    name: 'TemplateImport',
    components: {
        EntryPreview,
        LoadWrapper,
    },
    data () {
        return {
            selectedCourse: null,
            selectedAssignment: null,
            selectedTemplate: null,
            previewTemplate: null,
            importableTemplates: [],

            loading: true,
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
            return this.importableTemplates.find((importable) => importable.course.id === this.selectedCourse.id)
                .assignments
        },
    },
    created () {
        assignmentAPI.getImportable()
            .then((data) => {
                this.loading = false
                data.forEach((d) => {
                    d.assignments = d.assignments.filter((assignment) => assignment.id !== this.$route.params.aID)
                })
                this.importableTemplates = data.filter((d) => d.assignments.length > 0)
            })
    },
    methods: {
        ...mapMutations({
            templateSelected: 'assignmentEditor/SELECT_TEMPLATE',
        }),
        ...mapActions({
            create: 'template/create',
            list: 'template/list',
        }),
        importTemplate (template) {
            const payload = JSON.parse(JSON.stringify(template))
            payload.id = -1
            payload.categories = []

            this.create({ template: payload, aID: this.$route.params.aID, templateImport: true })
                .then((createdTemplate) => {
                    this.selectedCourse = null
                    this.selectedAssignment = null
                    this.selectedTemplate = null
                    this.previewTemplate = false

                    this.templateSelected({ template: createdTemplate })
                })
        },
        getTemplatesForSelectedAssignment () {
            this.list({ aID: this.selectedAssignment.id })
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
