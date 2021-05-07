<template>
    <section>
        <template v-if="presetNode">
            <sandboxed-iframe
                v-if="presetNode.description"
                :content="presetNode.description"
            />
            <files-list
                v-if="presetNode.attached_files && presetNode.attached_files.length > 0"
                class="mb-2 mr-2 align-top"
                :files="presetNode.attached_files"
            />
            <deadline-date-display
                class="mb-2 align-top"
                :subject="presetNode"
            />
        </template>

        <b-form-group
            v-if="template.allow_custom_title"
        >
            <template #label>
                <span class="field-heading optional">
                    Title
                </span>
                <tooltip tip="The title will also be displayed in the timeline."/>
            </template>
            <sandboxed-iframe
                v-if="template.title_description"
                :content="template.title_description"
            />
            <b-input class="input-disabled"/>
        </b-form-group>

        <entry-fields
            :template="template"
            :content="() => Object()"
            :edit="true"
            :readOnly="true"
        />
        <entry-categories
            :id="`template-${template.id}-preview`"
            :create="false"
            :edit="false"
            :entry="{}"
            :template="template"
            :displayOnly="true"
            class="mr-2 align-top"
        />
    </section>
</template>

<script>
import DeadlineDateDisplay from '@/components/assets/DeadlineDateDisplay.vue'
import EntryCategories from '@/components/category/EntryCategories.vue'
import EntryFields from '@/components/entry/EntryFields.vue'
import FilesList from '@/components/assets/file_handling/FilesList.vue'
import SandboxedIframe from '@/components/assets/SandboxedIframe.vue'

export default {
    name: 'EntryPreview',
    components: {
        DeadlineDateDisplay,
        EntryCategories,
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
