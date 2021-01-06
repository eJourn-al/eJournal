<template>
    <b-modal
        v-if="category"
        :id="id"
        size="lg"
        title="Category information"
        hideFooter
        noEnforceFocus
    >
        <b-card
            class="no-hover no-left-border"
        >
            <h2 class="theme-h2 multi-form">
                {{ category.name }}
            </h2>

            <sandboxed-iframe
                :content="category.description"
            />
        </b-card>
    </b-modal>
</template>

<script>
import SandboxedIframe from '@/components/assets/SandboxedIframe.vue'

export default {
    name: 'CategoryDisplay',
    components: {
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
