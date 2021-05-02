<template>
    <section>
        <b-card
            v-if="template.allow_custom_title"
            class="field-card background-light-grey"
        >
            <b-row
                alignH="between"
                noGutters
            >
                <b-col
                    cols="12"
                    sm="10"
                    lg="11"
                >
                    <b-input
                        class="mb-2 disabled"
                        placeholder="Title"
                        disabled
                    />
                    <text-editor
                        :id="`rich-text-editor-template-${template.id}-title-description`"
                        :key="`rich-text-editor-template-${template.id}-title-description`"
                        v-model="template.title_description"
                        :basic="true"
                        :displayInline="true"
                        :minifiedTextArea="true"
                        placeholder="Optional description"
                    />
                </b-col>
                <b-col
                    cols="12"
                    sm="2"
                    lg="1"
                    class="icon-box unselectable disabled"
                >
                    <div class="handle d-inline d-sm-block">
                        <icon
                            class="fill-grey"
                            name="arrows-alt"
                            scale="1.25"
                        />
                    </div>
                    <icon
                        class="fill-grey"
                        name="trash"
                        scale="1.25"
                        @click.native="$emit('removeField', field.location)"
                    />
                </b-col>
            </b-row>
        </b-card>

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

<style lang="sass">
.field-card
    .optional-field-template
        background-color: white
        color: $text-color !important
        svg
            fill: $theme-medium-grey

    .required-field-template
        background-color: $theme-dark-blue !important
        color: white !important
        svg, &:hover:not(.no-hover) svg
            fill: $theme-red !important

    &.sortable-chosen .card
        background-color: $border-color

    &.sortable-ghost
        opacity: 0.5

    &.sortable-drag .card
        visibility: visible

    .handle
        text-align: center
        padding-bottom: 7px

    .field-card:hover .move-icon, .field-card:hover .trash-icon
        fill: $theme-dark-blue !important

    .handle:hover .move-icon
        cursor: grab
        fill: $theme-blue !important

    .field-card:hover .trash-icon:hover
        fill: $theme-red !important

    .icon-box
        text-align: center

    @include sm-max
        .icon-box
            margin-top: 10px
</style>
