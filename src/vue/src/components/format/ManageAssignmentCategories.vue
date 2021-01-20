<template>
    <div
        v-intro="'Categories can be linked to student entries and be used to filter the timeline.'"
        v-intro-step="4"
        class="d-block"
    >
        <div v-b-tooltip:hover="(disabled) ? 'First save the changes made to the assignment' : ''">
            <b-button
                v-b-modal="'categories-modal'"
                class="orange-button full-width"
                :class="{'input-disabled': disabled}"
            >
                <icon name="layer-group"/>
                Manage Categories
            </b-button>
        </div>

        <b-modal
            id="categories-modal"
            size="xl"
            title="Manage Categories"
            hideFooter
            noEnforceFocus
        >
            <b-card
                class="no-hover no-left-border"
            >
                <h2 class="theme-h2 multi-form">
                    Create and remove or edit categories
                </h2>

                <p>
                    Categories can be linked to entries and be used to filter the timeline.
                    <br/><br/>
                    You can choose to link specific templates to categories. When a student makes use of these templates
                    to create an entry, the category will be linked to the entry by default.
                    Whether the student can edit which categories belonging to an entry can be configured via the
                    respective template setting "<i>Fixed Categories / Custom Categories</i>".
                </p>
                <b-table
                    id="user-table"
                    ref="table"
                    :items="categories"
                    :fields="fields"
                    :busy="categories === null"
                    responsive
                    striped
                    class="mt-2 mb-0 user-overview"
                    primary-key="id"
                    show-empty
                    empty-text="Create a category by clicking the button below"
                >
                    <template #table-busy>
                        <load-spinner class="mt-2"/>
                    </template>

                    <template #cell(name)="data">
                        <category-display
                            :id="`category-${data.item.id}-display`"
                            :editable="false"
                            :categories="[data.item]"
                        />
                    </template>

                    <template #cell(templates)="data">
                        <b-badge
                            v-for="template in data.item.templates"
                            :key="`category-${data.item.id}-template-${template.id}`"
                            class="mr-1"
                            pill
                        >
                            {{ template.name }}
                        </b-badge>
                    </template>

                    <template #cell(actions)="data">
                        <icon
                            name="edit"
                            class="edit-icon mr-2"
                            @click.native.stop="data.toggleDetails"
                        />

                        <icon
                            name="trash"
                            class="trash-icon"
                            @click.native.stop="deleteCategory(data.item)"
                        />
                    </template>

                    <template #row-details="data">
                        <category-edit
                            :ref="`category${data.item.id}Edit`"
                            :templates="templates"
                            :data="data.item"
                        />
                    </template>
                </b-table>

                <b-button
                    class="green-button mt-2 float-right"
                    @click="addCategory"
                >
                    <icon name="plus"/>
                    Add Category
                </b-button>
            </b-card>
        </b-modal>
    </div>
</template>

<script>
import CategoryDisplay from '@/components/category/CategoryDisplay.vue'
import CategoryEdit from '@/components/category/CategoryEdit.vue'
import colorUtils from '@/utils/colors.js'
import loadSpinner from '@/components/loading/LoadSpinner.vue'

export default {
    name: 'ManageAssignmentCategories',
    components: {
        loadSpinner,
        CategoryDisplay,
        CategoryEdit,
    },
    props: {
        templates: {
            required: true,
            type: Array,
        },
        disabled: {
            default: false,
            type: Boolean,
        },
    },
    data () {
        return {
            /* Decremented by one for each new local category, should be unique as it used as keys for the table. */
            newCategoryId: -1,
            fields: [
                {
                    key: 'name',
                    label: 'Name',
                },
                {
                    key: 'templates',
                    label: 'Templates',
                },
                {
                    key: 'actions',
                    label: '',
                },
            ],
        }
    },
    computed: {
        categories: {
            set () {
                /* Could be a strict mutation, but we allow _showDetails to be set in this component for ease of use */
            },
            get () { return this.$store.getters['category/assignmentCategories'] },
        },
    },
    methods: {
        deleteCategory (category) {
            if (category.id >= 0 && window.confirm(`Are you sure you want to delete ${category.name}?

This action will also immediately remove the category from any associated entries. \
This action cannot be undone.`)) {
                this.$store.dispatch('category/delete', { id: category.id })
            } else {
                this.$store.commit(
                    'category/deleteAssignmentCategory',
                    { id: category.id, aID: this.$route.params.aID },
                )
            }
        },
        addCategory () {
            this.categories.forEach((element) => { element._showDetails = false })

            this.categories.unshift({
                id: this.newCategoryId--,
                name: null,
                description: '',
                color: colorUtils.randomBrightRGBcolor(),
                templates: [],
                _showDetails: true,
            })
        },
    },
}
</script>
