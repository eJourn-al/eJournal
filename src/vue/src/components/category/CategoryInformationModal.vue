<template>
    <b-modal
        v-if="category"
        :id="id"
        size="lg"
        title="Category information"
        hideFooter
        noEnforceFocus
    >
        <b-form-group>
            <category-tag :category="category"/>
        </b-form-group>

        <b-form-group label="Description">
            <sandboxed-iframe
                v-if="category.description"
                :content="category.description"
            />
            <span
                v-else
                class="no-optional-content-value"
            >
                No description provided.
            </span>
        </b-form-group>
    </b-modal>
</template>

<script>
import CategoryTag from '@/components/category/CategoryTag.vue'
import SandboxedIframe from '@/components/assets/SandboxedIframe.vue'

export default {
    name: 'CategoryInformationModal',
    components: {
        CategoryTag,
        SandboxedIframe,
    },
    props: {
        category: {
            required: true,
        },
        id: {
            type: String,
            required: true,
        },
    },
}
</script>
