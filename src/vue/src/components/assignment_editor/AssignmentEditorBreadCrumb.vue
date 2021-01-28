<template>
    <bread-crumb>
        <assignment-editor-tutorial-icon @click.native.stop="$emit('start-tutorial')"/>
    </bread-crumb>
</template>

<script>
import AssignmentEditorTutorialIcon from '@/components/assignment_editor/AssignmentEditorTutorialIcon.vue'
import BreadCrumb from '@/components/assets/BreadCrumb.vue'

export default {
    name: 'AssignmentEditorBreadCrumb',
    components: {
        AssignmentEditorTutorialIcon,
        BreadCrumb,
    },
}
</script>
