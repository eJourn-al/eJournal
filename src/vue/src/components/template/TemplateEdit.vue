<template>
    <b-card
        :class="$root.getBorderClass($route.params.cID)"
        class="no-hover template-card"
    >
        <entry-preview
            v-if="readMode"
            :template="template"
        >
            <template #edit-button>
                <b-button
                    class="orange-button ml-auto"
                    @click="setModeToEdit()"
                >
                    <icon name="edit"/>
                    Edit
                </b-button>
            </template>
        </entry-preview>

        <template v-else>
            <b-row
                no-gutters
                class="multi-form"
            >
                <span class="theme-h2">
                    {{ (template.name) ? template.name : 'Template name' }}
                </span>

                <b-button
                    class="ml-auto"
                    :class="(create) ? 'green-button' : 'red-button'"
                    @click="(create) ? setModeToRead() : cancelTemplateEdit({ template })"
                >
                    <icon :name="(create) ? 'eye' : 'ban'"/>
                    {{ (create) ? 'Preview' : 'Cancel' }}
                </b-button>
            </b-row>

            <b-form-group
                label="Name"
                :invalid-feedback="nameInvalidFeedback"
                :state="nameInputState"
            >
                <b-input
                    v-model="template.name"
                    placeholder="Name"
                    class="theme-input"
                    type="text"
                    trim
                    required
                />
            </b-form-group>

            <template-edit-settings :template="template"/>

            <hr/>

            <template-edit-fields :template="template"/>

            <hr/>

            <template v-if="assignmentHasCategories">
                <b-form-group label="Categories">
                    <category-select
                        v-model="template.categories"
                        :options="assignmentCategories"
                        :openDirection="'top'"
                        placeholder="Set categories"
                    />
                </b-form-group>

                <hr/>
            </template>

            <b-row no-gutters>
                <b-button
                    v-if="!create"
                    class="red-button"
                    @click.stop="confirmDeleteTemplate()"
                >
                    <icon name="trash"/>
                    Delete
                </b-button>

                <b-button
                    class="green-button ml-auto"
                    @click="finalizeTemplateChanges"
                >
                    <icon :name="(create) ? 'plus' : 'save'"/>
                    {{ (create) ? 'Add Template' : 'Save' }}
                </b-button>
            </b-row>
        </template>
    </b-card>
</template>

<script>
import CategorySelect from '@/components/category/CategorySelect.vue'
import EntryPreview from '@/components/entry/EntryPreview.vue'
import TemplateEditFields from '@/components/template/TemplateEditFields.vue'
import TemplateEditSettings from '@/components/template/TemplateEditSettings.vue'

import { mapActions, mapGetters, mapMutations } from 'vuex'

export default {
    components: {
        CategorySelect,
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
        'template.name': {
            handler (name) {
                if (name === '') {
                    this.nameInvalidFeedback = 'Name cannot be empty'
                    this.nameInputState = false
                } else if (this.templates.some(elem => elem.id !== this.template.id && elem.name === name)) {
                    this.nameInvalidFeedback = 'Name is not unique'
                    this.nameInputState = false
                } else {
                    this.nameInputState = null
                }
            },
        },
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
        finalizeTemplateChanges () {
            if (this.nameInputState === false) {
                this.$toasted.error(this.nameInvalidFeedback)
                return
            }

            if (this.create) {
                this.createTemplate({ template: this.template, aID: this.$route.params.aID })
                    .then((template) => { this.templateCreated({ template }) })
            } else {
                this.updateTemplate({ id: this.template.id, data: this.template, aID: this.$route.params.aID })
                    .then(() => { this.templateUpdated({ template: this.template }) })
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
