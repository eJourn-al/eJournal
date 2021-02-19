<template>
    <b-card
        :class="$root.getBorderClass($route.params.cID)"
        class="no-hover"
    >
        <b-row
            no-gutters
            class="multi-form"
        >
            <span class="theme-h2">
                {{ (category.name) ? category.name : 'Category name' }}
            </span>

            <b-button
                class="ml-auto"
                :class="headerButtonClass"
                @click="changeMode()"
            >
                <icon :name="headerButtonIconName"/>
                {{ headerButtonText }}
            </b-button>
        </b-row>

        <category-read-mode
            v-if="readMode"
            :category="category"
        />

        <template v-else>
            <b-form-row>
                <b-col>
                    <b-form-group
                        label="Name"
                        class="required"
                        :invalid-feedback="nameInvalidFeedback"
                        :state="nameInputState"
                    >
                        <b-form-input
                            v-model="category.name"
                            autofocus
                            placeholder="Name"
                            class="theme-input"
                            type="text"
                            trim
                        />
                    </b-form-group>
                </b-col>

                <b-col cols="auto">
                    <b-form-group
                        label="Color"
                        class="required"
                    >
                        <b-input
                            v-model="category.color"
                            class="category-color-picker"
                            type="color"
                        />
                    </b-form-group>
                </b-col>
            </b-form-row>

            <b-form-group label="Description">
                <text-editor
                    :id="descriptionTextEditorID"
                    :key="descriptionTextEditorID"
                    ref="descriptionTextEditor"
                    v-model="category.description"
                    :footer="false"
                    :basic="true"
                    placeholder="Description"
                />
            </b-form-group>

            <b-form-group label="Templates">
                <theme-select
                    v-model="category.templates"
                    label="name"
                    trackBy="id"
                    :options="templates"
                    :multiple="true"
                    :searchable="true"
                    :multiSelectText="`template${category.templates.length > 1 ? 's' : ''}`"
                    placeholder="Add or remove templates"
                />
            </b-form-group>

            <hr/>

            <b-row no-gutters>
                <b-button
                    v-if="!create"
                    class="red-button"
                    @click.stop="confirmDeleteCategory()"
                >
                    <icon name="trash"/>
                    Delete
                </b-button>

                <b-button
                    class="green-button ml-auto"
                    @click="finalizeCategoryChanges"
                >
                    <icon :name="(create) ? 'plus' : 'save'"/>
                    {{ (create) ? 'Add Category' : 'Save' }}
                </b-button>
            </b-row>
        </template>
    </b-card>
</template>

<script>
import { mapActions, mapGetters, mapMutations } from 'vuex'

import CategoryReadMode from '@/components/category/CategoryReadMode.vue'

export default {
    name: 'CategoryEdit',
    components: {
        textEditor: () => import(/* webpackChunkName: 'text-editor' */ '@/components/assets/TextEditor.vue'),
        CategoryReadMode,
    },
    props: {
        category: {
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
            categories: 'category/assignmentCategories',
            templates: 'template/assignmentTemplates',
            readMode: 'assignmentEditor/readMode',
        }),
        create () {
            return this.category.id < 0
        },
        headerButtonText () {
            if (this.readMode) { return 'Edit' }
            return (this.create) ? 'Preview' : 'Cancel'
        },
        headerButtonClass () {
            if (this.readMode) { return 'orange-button' }
            return (this.create) ? 'green-button' : 'red-button'
        },
        headerButtonIconName () {
            if (this.readMode) { return 'edit' }
            return (this.create) ? 'eye' : 'ban'
        },
        descriptionTextEditorID () { return `text-editor-category-${this.category.id}-description` },
        validCategory () {
            return (
                this.nameInputState !== false
                && this.colorInputState !== false
            )
        },
    },
    watch: {
        'category.name': 'validateNameInput',
    },
    methods: {
        ...mapActions({
            cancelCategoryEdit: 'assignmentEditor/cancelCategoryEdit',
            categoryCreated: 'assignmentEditor/categoryCreated',
            categoryDeleted: 'assignmentEditor/categoryDeleted',
            categoryUpdated: 'assignmentEditor/categoryUpdated',
            categoryCreate: 'category/create',
            categoryDelete: 'category/delete',
            categoryUpdate: 'category/update',
        }),
        ...mapMutations({
            setModeToEdit: 'assignmentEditor/SET_ACTIVE_COMPONENT_MODE_TO_EDIT',
            setModeToRead: 'assignmentEditor/SET_ACTIVE_COMPONENT_MODE_TO_READ',
        }),
        validateNameInput () {
            const name = this.category.name

            if (name === '') {
                this.nameInvalidFeedback = 'Name cannot be empty.'
                this.nameInputState = false
            } else if (this.categories.some((cat) => cat.id !== this.category.id && cat.name === name)) {
                this.nameInvalidFeedback = 'Name is not unique.'
                this.nameInputState = false
            } else {
                this.nameInputState = null
            }
        },
        changeMode () {
            if (this.readMode) {
                this.setModeToEdit()
            } else {
                if (!this.create) {
                    this.cancelCategoryEdit({ category: this.category })
                }
                this.setModeToRead()
            }
        },
        finalizeCategoryChanges () {
            if (!this.validateData()) { return }

            if (this.create) {
                this.categoryCreate({ category: this.category, aID: this.$route.params.aID })
                    .then((category) => { this.categoryCreated({ category }) })
            } else {
                this.categoryUpdate({ id: this.category.id, category: this.category, aID: this.$route.params.aID })
                    .then((category) => { this.categoryUpdated({ category }) })
            }
        },
        confirmDeleteCategory () {
            if (window.confirm(`
Are you sure you want to delete ${this.category.name}?

This action will also remove the category from any associated entries. This action cannot be undone.`)) {
                this.categoryDelete({ id: this.category.id })
                    .then(() => { this.categoryDeleted({ category: this.category }) })
            }
        },
    },
}
</script>

<style lang="sass">
.category-color-picker
    width: 3em
</style>
