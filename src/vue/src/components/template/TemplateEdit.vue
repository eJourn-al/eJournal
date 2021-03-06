<template>
    <b-card class="template-card">
        <template #header>
            <template v-if="readMode">
                <b-button
                    class="grey-button float-right ml-2"
                    @click="setModeToEdit()"
                >
                    <icon name="edit"/>
                    Edit
                </b-button>
                <b-button
                    v-if="!create"
                    class="red-button float-right"
                    @click.stop="confirmDeleteTemplate()"
                >
                    <icon name="trash"/>
                    Delete
                </b-button>
            </template>
            <b-button
                v-else
                class="float-right ml-2"
                :class="(create) ? 'green-button' : 'red-button'"
                @click="(create) ? setModeToRead() : cancelTemplateEdit({ template })"
            >
                <icon :name="(create) ? 'eye' : 'ban'"/>
                {{ (create) ? 'Preview' : 'Cancel' }}
            </b-button>
            <h2 class="theme-h2">
                {{ (template.name) ? template.name : 'Template' }}
            </h2>
        </template>

        <entry-preview
            v-if="readMode"
            :template="template"
        />
        <template v-else>
            <b-form-group
                label="Name"
                class="required"
                :invalid-feedback="nameInvalidFeedback"
                :state="nameInputState"
            >
                <b-input
                    v-model="template.name"
                    placeholder="Name"
                    type="text"
                    trim
                    required
                />
            </b-form-group>

            <template-edit-settings
                class="mb-3"
                :template="template"
            />

            <template-edit-fields :template="template"/>
        </template>

        <template
            v-if="!readMode"
            #footer
        >
            <b-button
                class="green-button float-right"
                @click="finalizeTemplateChanges"
            >
                <icon :name="(create) ? 'plus' : 'save'"/>
                {{ (create) ? 'Add Template' : 'Save' }}
            </b-button>
        </template>
    </b-card>
</template>

<script>
import EntryPreview from '@/components/entry/EntryPreview.vue'
import TemplateEditFields from '@/components/template/TemplateEditFields.vue'
import TemplateEditSettings from '@/components/template/TemplateEditSettings.vue'

import { mapActions, mapGetters, mapMutations } from 'vuex'

export default {
    components: {
        EntryPreview,
        TemplateEditFields,
        TemplateEditSettings,
    },
    props: {
        template: {
            required: true,
            type: Object,
        },
    },
    data () {
        return {
            nameInvalidFeedback: null,
            nameInputState: null,
        }
    },
    computed: {
        ...mapGetters({
            readMode: 'assignmentEditor/readMode',
            assignmentCategories: 'category/assignmentCategories',
            assignmentHasCategories: 'category/assignmentHasCategories',
            templates: 'template/assignmentTemplates',
        }),
        create () { return this.template.id < 0 },
    },
    watch: {
        'template.name': 'validateNameInput',
    },
    methods: {
        ...mapMutations({
            setModeToEdit: 'assignmentEditor/SET_ACTIVE_COMPONENT_MODE_TO_EDIT',
            setModeToRead: 'assignmentEditor/SET_ACTIVE_COMPONENT_MODE_TO_READ',
        }),
        ...mapActions({
            cancelTemplateEdit: 'assignmentEditor/cancelTemplateEdit',
            templateCreated: 'assignmentEditor/templateCreated',
            templateDeleted: 'assignmentEditor/templateDeleted',
            templateUpdated: 'assignmentEditor/templateUpdated',
            createTemplate: 'template/create',
            updateTemplate: 'template/update',
            deleteTemplate: 'template/delete',
        }),
        validateNameInput () {
            const name = this.template.name

            if (name === '') {
                this.nameInvalidFeedback = 'Name cannot be empty.'
                this.nameInputState = false
            } else if (this.templates.some((elem) => elem.id !== this.template.id && elem.name === name)) {
                this.nameInvalidFeedback = 'Name is not unique.'
                this.nameInputState = false
            } else {
                this.nameInputState = null
            }
        },
        finalizeTemplateChanges () {
            if (!this.validateData()) { return }

            if (this.create) {
                this.createTemplate({ template: this.template, aID: this.$route.params.aID })
                    .then((template) => {
                        this.templateCreated({ template, fromPresetNode: this.template.fromPresetNode })
                    })
            } else {
                this.updateTemplate({ id: this.template.id, data: this.template, aID: this.$route.params.aID })
                    .then((updatedTemplate) => {
                        this.templateUpdated({ updatedTemplate, oldTemplateId: this.template.id })
                    })
            }
        },
        confirmDeleteTemplate () {
            if (window.confirm(
                `Are you sure you want to delete template "${this.template.name}" from the assignment?`)) {
                this.deleteTemplate({ id: this.template.id, aID: this.$route.params.aID })
                    .then(() => { this.templateDeleted({ template: this.template }) })
            }
        },
    },
}
</script>
