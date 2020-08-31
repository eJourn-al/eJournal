<template>
    <b-card class="no-hover">
        <div class="d-flex">
            <b-button
                :class="{'active': mode === 'edit'}"
                class="multi-form change-button flex-basis-100"
                @click="mode = 'edit'"
            >
                <icon name="edit"/>
                Edit
            </b-button>
            <b-button
                :class="{'active': mode === 'preview'}"
                class="multi-form add-button flex-basis-100"
                @click="mode='preview'"
            >
                <icon name="eye"/>
                Preview
            </b-button>
        </div>
        <hr/>
        <div v-show="mode === 'edit'">
            <b-input
                id="template-name"
                v-model="template.name"
                class="mr-sm-2 multi-form theme-input"
                placeholder="Template name"
                required
            />
            <div
                v-if="template.preset_only"
                class="template-availability"
            >
                <b-button
                    class="delete-button"
                    @click.stop
                    @click="togglePresetOnly"
                >
                    <icon name="lock"/>
                    Preset-only
                </b-button>
                <icon
                    name="info-circle"
                    class="shift-up-3"
                />
                This template can only be used for preset entries you add to the timeline
            </div>
            <div
                v-if="!template.preset_only"
                class="template-availability"
            >
                <b-button
                    class="add-button"
                    @click.stop
                    @click="togglePresetOnly"
                >
                    <icon name="unlock"/>
                    Unlimited
                </b-button>
                <icon
                    name="info-circle"
                    class="shift-up-3"
                />
                This template can be freely used by students as often as they want<br/>
            </div>
            <draggable
                v-model="template.field_set"
                handle=".handle"
                @start="startDrag"
                @end="endDrag"
                @update="onUpdate"
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
                class="add-button full-width"
                @click="addField"
            >
                <icon name="plus"/>
                Add field
            </b-button>
        </div>
        <entry-fields
            v-if="mode !== 'edit'"
            :template="template"
            :content="() => Object()"
            :edit="true"
            :readOnly="true"
        />
    </b-card>
</template>

<script>
import EntryFields from '@/components/entry/EntryFields.vue'
// Try changing below import (and filename in tree) to TemplateField.vue: why is it specifically unresolved?
import TemplateField from '@/components/template/Field.vue'
import draggable from 'vuedraggable'

export default {
    components: {
        draggable,
        EntryFields,
        TemplateField,
    },
    props: {
        template: {
            required: true,
        },
    },
    data () {
        return {
            mode: 'edit',
            selectedLocation: null,
            showEditors: true,
        }
    },
    created () {
        this.template.field_set.sort((a, b) => a.location - b.location)
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
        startDrag () {
            this.showEditors = false
        },
        endDrag () {
            this.showEditors = true
        },
        onUpdate () {
            this.updateLocations()
        },
        togglePresetOnly () {
            this.template.preset_only = !this.template.preset_only
        },
    },
}
</script>

<style lang="sass">
@import '~sass/modules/colors.sass'
@import '~sass/modules/breakpoints.sass'

.optional-field-template
    background-color: white
    color: $theme-dark-blue !important
    svg
        fill: $theme-medium-grey

.required-field-template
    background-color: $theme-dark-blue !important
    color: white !important
    svg, &:hover:not(.no-hover) svg
        fill: $theme-red !important

#template-name
    font-weight: bold
    font-size: 1.8em
    font-family: 'Roboto', sans-serif
    color: $theme-dark-blue

.sortable-chosen .card
    background-color: $theme-dark-grey

.sortable-ghost
    visibility: hidden

.sortable-drag .card
    visibility: visible

.icon-box
    text-align: center

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

@include sm-max
    .icon-box
        margin-top: 10px

.template-availability
    font-weight: bold
    color: grey
    margin-bottom: 10px
    .btn
        margin-right: 20px
        @include md-max
            width: 100%
            margin-bottom: 10px
</style>
