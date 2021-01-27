<template>
    <div>
        <h3
            class="theme-h3 cursor-pointer unselectable"
            @click="expanded = !expanded"
        >
            Categories
            <icon :name="(expanded) ? 'angle-down' : 'angle-up'"/>
        </h3>

        <div
            v-if="expanded"
            class="d-block"
        >
            <b-card
                :class="$root.getBorderClass($route.params.cID)"
                class="no-hover"
            >
                <b-row
                    v-if="assignmentHasCategories"
                    no-gutters
                    class="template-list-header"
                >
                    <b>Name</b>
                </b-row>

                <category-menu-item
                    v-for="category in categories"
                    :key="`category-${category.id}-menu-item`"
                    :category="category"
                    @delete-category="deleteCategory($event)"
                    @select-category="selectCategory({ category: $event })"
                />

                <b-button
                    class="green-button mt-2 full-width"
                    @click="createCategory()"
                >
                    <icon name="plus"/>
                    Create New Category
                </b-button>
            </b-card>
        </div>
    </div>
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
            }
        },
    },
}
</script>

<style lang="sass">
.template-list-header
    border-bottom: 2px solid $theme-dark-grey

.template-link
    padding: 5px
    border-bottom: 1px solid $theme-dark-grey
    cursor: pointer
    vertical-align: middle
    svg
        margin-top: 3px
    .max-one-line
        width: calc(100% - 2em)
    .edit-icon
        margin-top: 4px
    .edit-icon, .trash-icon
        width: 0px
        visibility: hidden
    &:hover
        background-color: $theme-dark-grey
        .max-one-line
            width: calc(100% - 5em)
        .edit-icon, .trash-icon
            visibility: visible
            width: auto
    &.active
        background-color: $theme-dark-grey
</style>
