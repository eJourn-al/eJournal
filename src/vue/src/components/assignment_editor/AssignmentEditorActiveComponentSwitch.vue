<template>
    <div>
        <template-edit
            v-if="activeComponent === activeComponentOptions.template"
            :template="selectedTemplate"
        />

        <template-import v-else-if="activeComponent === activeComponentOptions.templateImport"/>

        <category-edit
            v-else-if="activeComponent === activeComponentOptions.category"
            :category="selectedCategory"
        />

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
import CategoryEdit from '@/components/category/CategoryEdit.vue'
import SelectedTimelineComponentSwitch from
    '@/components/assignment_editor/timeline_controlled/SelectedTimelineComponentSwitch.vue'
import TemplateEdit from '@/components/template/TemplateEdit.vue'
import TemplateImport from '@/components/template/TemplateImport.vue'

import { mapGetters } from 'vuex'

export default {
    name: 'AssignmentEditorActiveComponentSwitch',
    components: {
        CategoryEdit,
        SelectedTimelineComponentSwitch,
        TemplateEdit,
        TemplateImport,
    },
    computed: {
        ...mapGetters({
            activeComponent: 'assignmentEditor/activeComponent',
            activeComponentOptions: 'assignmentEditor/activeComponentOptions',
            selectedCategory: 'assignmentEditor/selectedCategory',
            selectedTemplate: 'assignmentEditor/selectedTemplate',
        }),
    },
}
</script>
