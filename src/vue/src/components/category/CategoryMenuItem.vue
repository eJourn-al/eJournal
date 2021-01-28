<template>
    <div
        class="menu-item-link unselectable"
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
            selectedCategory: 'assignmentEditor/selectedCategory',
            activeComponentOptions: 'assignmentEditor/activeComponentOptions',
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
