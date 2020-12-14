<template>
    <div
        v-intro="'TODO'"
        v-intro-step="4"
        class="d-block"
    >
        <b-button
            v-b-modal="'categories-modal'"
            class="orange-button mt-2 full-width"
        >
            <icon name="layer-group"/>
            Manage Categories
        </b-button>

        <b-modal
            id="categories-modal"
            size="lg"
            title="Manage Categories"
            hideFooter
            noEnforceFocus
        >
            <b-card
                class="no-hover no-left-border"
            >
                <h2 class="theme-h2 multi-form">
                    Create, remove or edit categories
                </h2>

                <p>
                    TODO Categories description
                </p>
                <!-- eslint-disable vue/attribute-hyphenation -->
                <b-table
                    id="user-table"
                    ref="table"
                    :items="provider"
                    :fields="fields"
                    responsive
                    striped
                    class="mt-2 mb-0 user-overview"
                    primary-key="id"
                    show-empty
                    empty-text="Create a category by clicking the button below"
                >
                    <!-- eslint-enable vue/attribute-hyphenation -->
                    <template #table-busy>
                        <load-spinner class="mt-2"/>
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
                        <edit-category
                            :templates="templates"
                            :data="data.item"
                        />

                        <b-button
                            class="green-button float-right"
                            @click="patchCategory(data)"
                        >
                            <icon name="save"/>
                            Save Category
                        </b-button>
                    </template>
                </b-table>

                <b-button
                    v-if="!newCategory"
                    class="green-button mt-2 float-right"
                    @click="addCategory"
                >
                    <icon name="plus"/>
                    Add Category
                </b-button>

                <template v-if="newCategory">
                    <hr/>

                    <edit-category
                        :templates="templates"
                        :data="newCategory"
                    />

                    <b-button
                        class="green-button mt-2 float-right"
                        @click="createCategory"
                    >
                        <icon name="save"/>
                        Save Category
                    </b-button>
                </template>
            </b-card>
        </b-modal>
    </div>
</template>

<script>
import categoryAPI from '@/api/category.js'
import editCategory from '@/components/format/EditCategory.vue'
import loadSpinner from '@/components/loading/LoadSpinner.vue'

export default {
    name: 'Categories',
    components: {
        loadSpinner,
        editCategory,
    },
    props: {
        templates: {
            required: true,
            type: Array,
        },
    },
    data () {
        return {
            newCategory: null,
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
    methods: {
        provider (context, callback) {
            categoryAPI.list(this.$route.params.aID)
                .then((data) => {
                    /* Transform template ids to template data objects */
                    data.map((category) => {
                        category.templates = category.templates.map(
                            templateID => this.templates.find(template => template.id === templateID))
                        return category
                    })

                    callback(data)
                })
                .catch(() => {
                    callback([])
                })

            return null
        },
        patchCategory (data) {
            const payload = JSON.parse(JSON.stringify(data.item))
            payload.templates = data.item.templates.map(elem => elem.id)

            categoryAPI.update(payload.id, payload, { customSuccessToast: `${payload.name} succesfully updated.` })
                .then(() => { data.toggleDetails() })
        },
        deleteCategory (category) {
            categoryAPI.delete(category.id)
                .then(() => { this.$refs.table.refresh() })
        },
        addCategory () {
            this.newCategory = {
                id: -1,
                name: null,
                description: '',
                templates: [],
            }
        },
        createCategory () {
            const payload = JSON.parse(JSON.stringify(this.newCategory))
            payload.templates = this.newCategory.templates.map(elem => elem.id)
            payload.assignment_id = this.$route.params.aID

            categoryAPI.create(payload, { customSuccessToast: `${payload.name} succesfully created.` })
                .then(() => {
                    this.newCategory = null
                    this.$refs.table.refresh()
                })
        },
    },
}
</script>
