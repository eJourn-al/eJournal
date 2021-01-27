<template>
    <div>
        <template-edit
            v-if="activeComponent === activeComponentOptions.template"
            :template="selectedTemplate"
        />

        <template-import v-else-if="activeComponent === activeComponentOptions.templateImport"/>

        <selected-timeline-component-switch v-else-if="activeComponent === activeComponentOptions.timeline"/>

        <b-card
            v-else
            :class="$root.getBorderClass($route.params.cID)"
        >
            Select any item to get started.
        </b-card>
    </div>
</template>

<script>
import SelectedTimelineComponentSwitch from
    '@/components/format/timeline_controlled/SelectedTimelineComponentSwitch.vue'
import TemplateEdit from '@/components/template/TemplateEdit.vue'
import TemplateImport from '@/components/template/TemplateImport.vue'

import { mapGetters } from 'vuex'

export default {
    name: 'FormatActiveComponents',
    components: {
        SelectedTimelineComponentSwitch,
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
