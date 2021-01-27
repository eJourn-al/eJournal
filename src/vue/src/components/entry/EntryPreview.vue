<template>
    <section>
        <b-row
            no-gutters
            class="multi-form"
        >
            <span class="theme-h2">
                {{ (presetNode) ? presetNode.display_name : template.name }}
            </span>

            <slot name="edit-button"/>
        </b-row>

        <entry-fields
            :template="template"
            :content="() => Object()"
            :edit="true"
            :readOnly="true"
        />
        <category-display
            :id="`template-${template.id}-preview`"
            :template="template"
            :categories="template.categories"
        />
    </section>
</template>

<script>
import CategoryDisplay from '@/components/category/CategoryDisplay.vue'
import EntryFields from '@/components/entry/EntryFields.vue'

export default {
    name: 'EntryPreview',
    components: {
        CategoryDisplay,
        EntryFields,
    },
    props: {
        template: {
            required: true,
        },
        presetNode: {
            default: null,
        },
    },
}
</script>
