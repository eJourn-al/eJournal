<template>
    <section>
        <h3 class="theme-h3">
            Actions
        </h3>

        <manage-assignment-categories/>
    </section>
</template>

<script>
import ManageAssignmentCategories from '@/components/format/ManageAssignmentCategories.vue'

export default {
    name: 'FormatActions',
    components: {
        ManageAssignmentCategories,
    },
}
</script>
