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

        <color-picker
            v-model="data.color"
            :height="100"
            :width="100"
        />
    </div>
</template>

<script>
import ColorPicker from 'vue-color-picker-wheel'

export default {
    name: 'CategoryEdit',
    components: {
        ColorPicker,
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
    data () {
        return {
            updateCall: null,
            color: '#ffffff',
        }
    },
    watch: {
        data: {
            deep: true,
            handler (val) {
                if (val.id !== -1) {
                    this.patchCategory(val)
                }
            },
        },
    },
    methods: {
        patchCategory (data) {
            window.clearTimeout(this.updateCall)

            const payload = JSON.parse(JSON.stringify(data))
            payload.templates = data.templates.map(elem => elem.id)

            this.updateCall = window.setTimeout(() => {
                this.$store.dispatch('category/update', { id: payload.id, data: payload })
            }, 3000)
        },
    },
}
</script>
