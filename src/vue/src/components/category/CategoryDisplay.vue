<template>
    <div>
        <category-tag
            v-for="category in categories"
            :key="`${id}-category-${category.id}`"
            v-b-modal="`${id}-category-information`"
            :category="category"
            :removable="editable"
            @select-category="selectedCategory = category"
            @remove-category="$emit('remove-category', category)"
        />

        <slot/>

        <category-information-modal
            :id="`${id}-category-information`"
            :category="selectedCategory"
        />
    </div>
</template>

<script>
import CategoryInformationModal from '@/components/category/CategoryInformationModal.vue'
import CategoryTag from '@/components/category/CategoryTag.vue'

export default {
    name: 'CategoryDisplay',
    components: {
        CategoryInformationModal,
        CategoryTag,
    },
    props: {
        categories: {
            required: true,
            type: Array,
        },
        id: {
            type: String,
            required: true,
        },
        editable: {
            default: false,
        },
    },
    data () {
        return {
            selectedCategory: null,
        }
    },
}
</script>
