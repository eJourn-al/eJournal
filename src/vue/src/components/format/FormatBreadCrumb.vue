<template>
    <bread-crumb>
        <format-tutorial-icon @click.native.stop="$emit('start-tutorial')"/>
    </bread-crumb>
</template>

<script>
import BreadCrumb from '@/components/assets/BreadCrumb.vue'
import FormatTutorialIcon from '@/components/format/FormatTutorialIcon.vue'

export default {
    name: 'FormatBreadCrumb',
    components: {
        BreadCrumb,
        FormatTutorialIcon,
    },
}
</script>
