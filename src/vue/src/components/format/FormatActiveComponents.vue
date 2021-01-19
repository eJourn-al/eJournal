<template>
    <section>
        <template-edit
            v-if="activeComponent === activeComponentOptions.template"
            :template="selectedTemplate"
        />

        <template-import v-else-if="activeComponent === activeComponentOptions.templateImport"/>

        <b-card
            v-else
            :class="$root.getBorderClass($route.params.cID)"
        >
            Select any item to get started.
        </b-card>
    </section>
</template>

<script>
import TemplateEdit from '@/components/template/TemplateEdit.vue'
import TemplateImport from '@/components/template/TemplateImport.vue'

import { mapGetters } from 'vuex'

export default {
    name: 'FormatActiveComponents',
    components: {
        TemplateEdit,
        TemplateImport,
    },
    props: {
    },
    computed: {
        ...mapGetters({
            activeComponent: 'assignmentEditor/activeComponent',
            activeComponentOptions: 'assignmentEditor/activeComponentOptions',
            selectedTemplate: 'assignmentEditor/selectedTemplate',
        }),
    },
}
</script>

<style>

</style>
