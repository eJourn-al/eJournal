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

        <template v-if="presetNode">
            <sandboxed-iframe
                v-if="presetNode.description"
                :content="presetNode.description"
            />
            <files-list :files="presetNode.attached_files"/>
        </template>

        <b-form-group
            v-if="template.allow_custom_title"
            label="Title"
        >
            <sandboxed-iframe
                v-if="template.title_description"
                :content="template.title_description"
            />
            <b-input class="theme-input input-disabled"/>
        </b-form-group>

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
import FilesList from '@/components/assets/file_handling/FilesList.vue'
import SandboxedIframe from '@/components/assets/SandboxedIframe.vue'

export default {
    name: 'EntryPreview',
    components: {
        CategoryDisplay,
        EntryFields,
        FilesList,
        SandboxedIframe,
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
