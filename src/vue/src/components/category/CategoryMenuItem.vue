<template>
    <div
        class="template-link"
        :class="{ active: isActive }"
        @click="$emit('select-category', category)"
    >
        <category-tag
            :category="category"
            :removable="false"
            :showInfo="false"
        />

        <icon
            name="trash"
            class="trash-icon ml-2 float-right"
            @click.native.stop="$emit('delete-category', category)"
        />
    </div>
</template>

<script>
import CategoryTag from '@/components/category/CategoryTag.vue'

import { mapGetters } from 'vuex'

export default {
    name: 'CategoryMenuItem',
    components: {
        CategoryTag,
    },
    props: {
        category: {
            required: true,
            type: Object,
        },
    },
    computed: {
        ...mapGetters({
            activeComponent: 'assignmentEditor/activeComponent',
            selectedTemplate: 'assignmentEditor/selectedTemplate',
            activeComponentOptions: 'assignmentEditor/activeComponentOptions',
        }),
        isActive () {
            return (
                this.activeComponent === this.activeComponentOptions.category
                && this.selectedCategory === this.category
            )
        },
    },
}
</script>

<style lang="sass">
// TODO Category: Extract and centralize
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
