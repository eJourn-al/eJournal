<template>
    <div
        class="menu-item-link unselectable"
        :class="{ active: isActive }"
        @click="$emit('select-category', category)"
    >
        <span :class="{ dirty: isCategoryDirty(category) }">
            <category-tag
                :category="category"
                :removable="false"
                :showInfo="false"
            />
        </span>

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
            selectedCategory: 'assignmentEditor/selectedCategory',
            activeComponentOptions: 'assignmentEditor/activeComponentOptions',
            isCategoryDirty: 'assignmentEditor/isCategoryDirty',
        }),
        isActive () {
            return (
                this.activeComponent === this.activeComponentOptions.category
                && this.selectedCategory.id === this.category.id
            )
        },
    },
}
</script>

<style lang="sass" scoped>
.category-tag
    margin-right: 0px
</style>
