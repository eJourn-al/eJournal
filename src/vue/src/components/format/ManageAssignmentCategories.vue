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
                    <!-- eslint-enable vue/attribute-hyphenation -->
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
                            :templates="templates"
                            :data="data.item"
                        />
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

                    <category-edit
                        :templates="templates"
                        :data="newCategory"
                    />
                </template>
            </b-card>
        </b-modal>
    </div>
</template>

<script>
import CategoryDisplay from '@/components/category/CategoryDisplay.vue'
import CategoryEdit from '@/components/category/CategoryEdit.vue'
import categoryAPI from '@/api/category.js'
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
            categories: null,
            createCall: null,
        }
    },
    watch: {
        newCategory: {
            deep: true,
            handler (category) {
                if (category && category.name) { this.createCategory() }
            },
        },
    },
    created () {
        categoryAPI.list(this.$route.params.aID).then((categories) => { this.categories = categories })
    },
    methods: {
        deleteCategory (category) {
            categoryAPI.delete(category.id)
                .then(() => { this.categories = this.categories.filter(elem => elem.id !== category.id) })
        },
        addCategory () {
            this.categories.forEach((element) => { element._showDetails = false })

            this.newCategory = {
                id: -1,
                name: null,
                description: '',
                color: colorUtils.randomBrightRGBcolor(),
                templates: [],
            }
        },
        createCategory () {
            window.clearTimeout(this.createCall)

            this.createCall = window.setTimeout(() => {
                const payload = JSON.parse(JSON.stringify(this.newCategory))
                payload.templates = this.newCategory.templates.map(elem => elem.id)
                payload.assignment_id = this.$route.params.aID

                categoryAPI.create(payload)
                    .then((category) => {
                        const latestCopy = JSON.parse(JSON.stringify(this.newCategory))
                        latestCopy._showDetails = true
                        latestCopy.id = category.id
                        this.categories.push(latestCopy)
                        this.newCategory = null
                    })
            }, 3000)
        },
    },
}
</script>
