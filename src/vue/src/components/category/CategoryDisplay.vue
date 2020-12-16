<template>
    <div>
        <b-badge
            v-for="category in categories"
            :key="`${id}-category-${category.id}`"
            v-b-modal="'category-information'"
            class="mr-1"
            :style="`background-color: ${category.color}`"
            pill
            @click.stop="selectedCategory = category"
        >
            {{ category.name }}
            <icon
                v-if="editable"
                class="fill-red ml-1"
                name="times"
                @click.stop.native="$emit('remove-category', category)"
            />
        </b-badge>

        <slot/>

        <b-modal
            v-if="selectedCategory"
            id="category-information"
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
import SandboxedIframe from '@/components/assets/SandboxedIframe.vue'

export default {
    name: 'CategoryDisplay',
    components: {
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
