<template>
    <section>
        <h2 class="theme-h2 multi-form">
            Fields
        </h2>

        <b-form-group
            v-if="template.allow_custom_title"
            label="Title"
        >
            <text-editor
                :id="`rich-text-editor-template-${template.id}-title-description`"
                :key="`rich-text-editor-template-${template.id}-title-description`"
                v-model="template.title_description"
                :basic="true"
                :displayInline="true"
                :minifiedTextArea="true"
                class="multi-form"
                placeholder="Optional description"
            />
        </b-form-group>

        <draggable
            v-model="template.field_set"
            handle=".handle"
            @start="showEditors = false"
            @end="showEditors = true"
            @update="updateLocations()"
        >
            <template-field
                v-for="field in template.field_set"
                :key="field.location"
                :field="field"
                :showEditors="showEditors"
                @removeField="removeField"
            />
            <div class="invisible"/>
        </draggable>

        <b-button
            class="green-button full-width"
            @click="addField"
        >
            <icon name="plus"/>
            Add field
        </b-button>
    </section>
</template>

<script>
import TemplateField from '@/components/template/TemplateField.vue'
import draggable from 'vuedraggable'

export default {
    name: 'TemplateEditFields',
    components: {
        draggable,
        TemplateField,
        TextEditor: () => import(/* webpackChunkName: 'text-editor' */ '@/components/assets/TextEditor.vue'),
    },
    props: {
        template: {
            required: true,
            type: Object,
        },
    },
    data () {
        return {
            selectedLocation: null,
            showEditors: true,
        }
    },
    methods: {
        updateLocations () {
            for (let i = 0; i < this.template.field_set.length; i++) {
                this.template.field_set[i].location = i
            }
        },
        addField () {
            const newField = {
                type: 'rt',
                title: '',
                description: '',
                options: null,
                location: this.template.field_set.length,
                required: true,
            }

            this.template.field_set.push(newField)
        },
        removeField (location) {
            if (this.template.field_set[location].title
                ? window.confirm(
                    `Are you sure you want to remove "${this.template.field_set[location].title}" from this template?`)
                : window.confirm('Are you sure you want to remove this field from this template?')) {
                this.template.field_set.splice(location, 1)
            }

            this.updateLocations()
        },
    },
}
</script>
