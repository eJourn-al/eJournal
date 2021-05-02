<template>
    <b-card>
        <template slot="header">
            <slot name="edit-button"/>
            <h2 class="theme-h2">
                End of assignment
            </h2>
        </template>
        <deadline-date-display :subject="assignment"/>
    </b-card>
</template>

<script>
import DeadlineDateDisplay from '@/components/assets/DeadlineDateDisplay.vue'

export default {
    components: {
        DeadlineDateDisplay,
    },
    props: ['assignment'],
}
</script>
