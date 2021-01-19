<template>
    <section>
        <h3 class="theme-h3">
            Actions
        </h3>

        <manage-assignment-categories
            ref="manageAssignmentCategories"
            :disabled="templatesChanged"
            :templates="templates"
        />
    </section>
</template>

<script>
import ManageAssignmentCategories from '@/components/format/ManageAssignmentCategories.vue'

export default {
    name: 'FormatActions',
    components: {
        ManageAssignmentCategories,
    },
    // TODO: Refactor (remove probably)
    props: ['templatesChanged', 'templates'],

}
</script>

<style>

</style>
