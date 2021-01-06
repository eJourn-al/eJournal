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

        <b-modal
            v-if="selectedCategory"
            :id="`${id}-category-information`"
            size="lg"
            title="Category information"
            hideFooter
            noEnforceFocus
        >
            <b-card
                class="no-hover no-left-border"
            >
                <h2 class="theme-h2 multi-form">
                    {{ selectedCategory.name }}
                </h2>

                <sandboxed-iframe
                    :content="selectedCategory.description"
                />
            </b-card>
        </b-modal>
    </div>
</template>

<script>
import CategoryTag from '@/components/category/CategoryTag.vue'
import SandboxedIframe from '@/components/assets/SandboxedIframe.vue'

export default {
    name: 'CategoryDisplay',
    components: {
        CategoryTag,
        SandboxedIframe,
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
