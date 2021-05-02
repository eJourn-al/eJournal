<template>
    <b-card>
        <template slot="header">
            <slot name="edit-button"/>
            <h2 class="theme-h2">
                Assignment details: {{ assignment.name }}
            </h2>
        </template>
        <sandboxed-iframe
            v-if="assignment.description"
            :content="assignment.description"
        />
        <i
            v-else
            class="text-grey d-block"
        >
            No description
        </i>
        <deadline-date-display
            class="mt-2"
            :subject="assignment"
        />
    </b-card>
</template>

<script>
import DeadlineDateDisplay from '@/components/assets/DeadlineDateDisplay.vue'
import sandboxedIframe from '@/components/assets/SandboxedIframe.vue'

export default {
    components: {
        DeadlineDateDisplay,
        sandboxedIframe,
    },
    props: ['assignment'],
}
</script>
