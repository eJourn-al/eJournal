<template>
    <b-card noBody>
        <div
            slot="header"
            class="cursor-pointer"
            @click="expanded = !expanded"
        >
            <h3 class="theme-h3 unselectable">
                Categories
            </h3>
            <icon
                :name="(expanded) ? 'angle-down' : 'angle-up'"
                class="float-right fill-grey mt-1 mr-1"
            />
        </div>

        <template v-if="expanded">
            <category-menu-item
                v-for="category in categories"
                :key="`category-${category.id}-menu-item`"
                :category="category"
                @delete-category="deleteCategory($event)"
                @select-category="selectCategory({ category: $event })"
            />

            <b-card-body class="p-2">
                <b-button
                    variant="link"
                    class="green-button"
                    @click="createCategory({ colorIndex: categories.length })"
                >
                    <icon name="plus"/>
                    Create New Category
                </b-button>
            </b-card-body>
        </template>
    </b-card>
</template>

<script>
import CategoryMenuItem from '@/components/category/CategoryMenuItem.vue'

import { mapActions, mapGetters, mapMutations } from 'vuex'

export default {
    name: 'ManageAssignmentCategories',
    components: {
        CategoryMenuItem,
    },
    data () {
        return {
            expanded: false,
        }
    },
    computed: {
        ...mapGetters({
            categories: 'category/assignmentCategories',
            assignmentHasCategories: 'category/assignmentHasCategories',
        }),
    },
    created () {
        this.expanded = this.assignmentHasCategories
    },
    methods: {
        ...mapActions({
            categoryDelete: 'category/delete',
            categoryDeleted: 'assignmentEditor/categoryDeleted',
        }),
        ...mapMutations({
            createCategory: 'assignmentEditor/CREATE_CATEGORY',
            selectCategory: 'assignmentEditor/SELECT_CATEGORY',
        }),
        deleteCategory (category) {
            if (window.confirm(`Are you sure you want to delete ${category.name}?
This action will also immediately remove the category from any associated entries. \
This action cannot be undone.`)) {
                this.categoryDelete({ id: category.id })
                    .then(() => { this.categoryDeleted({ category }) })
            }
        },
    },
}
</script>
