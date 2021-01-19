<template>
    <bread-crumb
        v-intro="'Welcome to the assignment editor!<br/>This is where you can configure the structure of \
        your assignment. Proceed with this tutorial to learn more.'"
        v-intro-step="1"
    >
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
