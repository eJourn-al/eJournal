<template>
    <div>
        <b-input
            v-model="data.name"
            palceholder="Name"
            class="theme-input multi-form"
            type="text"
        />

        <text-editor
            :id="`text-editor-category-${data.id}-description`"
            :key="`text-editor-category-${data.id}-description`"
            v-model="data.description"
            :footer="false"
            class="multi-form"
            placeholder="Description"
        />

        <theme-select
            v-model="data.templates"
            label="name"
            trackBy="id"
            :options="templates"
            :multiple="true"
            :searchable="true"
            :multiSelectText="`template${data.templates.length > 1 ? 's' : ''}`"
            placeholder="Search and add or remove templates"
            class="multi-form"
        />
    </div>
</template>

<script>
export default {
    name: 'EditCategory',
    components: {
        textEditor: () => import(/* webpackChunkName: 'text-editor' */ '@/components/assets/TextEditor.vue'),
    },
    props: {
        data: {
            required: true,
            type: Object,
        },
        templates: {
            required: true,
            type: Array,
        },
    },
}
</script>
