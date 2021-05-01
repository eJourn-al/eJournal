<template>
    <h2 class="theme-h2">
        {{ title }}
    </h2>
</template>

<script>
export default {
    name: 'EntryTitle',
    props: {
        template: {
            required: true,
            type: Object,
        },
        /* Node can be a normal node (to be created or not), or a preset node. */
        node: {
            required: true,
            type: Object,
        },
    },
    computed: {
        title () {
            if (this.node.entry && 'title' in this.node.entry) {
                return this.node.entry.title /* Set backend, this should always be correct */
            }

            if (this.node.display_name) {
                return this.node.display_name
            }

            return this.template.name
        },
    },
}
</script>
