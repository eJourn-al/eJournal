<!--
    Used in a card in the format editor to open template editor and delete templates from pool.
-->

<template>
    <div
        class="template-link unselectable"
        :class="{ active: isActive }"
        @click="$emit('select-template', template)"
    >
        <icon
            v-b-tooltip:hover="(template.preset_only) ?
                'This template can only be used for preset entries you add to the timeline'
                : 'This template can be freely used by students as often as they want'
            "
            :name="(template.preset_only) ? 'lock' : 'unlock'"
            class="float-right ml-2"
            :class="(template.preset_only) ? 'fill-red' : 'fill-green'"
        />

        <icon
            name="trash"
            class="trash-icon ml-2 float-right"
            @click.native.stop="$emit('delete-template', template)"
        />

        <b class="max-one-line">
            {{ template.name }}
        </b>
    </div>
</template>

<script>
import { mapGetters } from 'vuex'

export default {
    name: 'TemplateMenuItem',
    props: {
        template: {
            required: true,
            type: Object,
        },
    },
    computed: {
        ...mapGetters({
            activeComponent: 'assignmentEditor/activeComponent',
            selectedTemplate: 'assignmentEditor/selectedTemplate',
            activeComponentOptions: 'assignmentEditor/activeComponentOptions',
        }),
        isActive () {
            return (
                this.activeComponent === this.activeComponentOptions.template
                && this.selectedTemplate === this.template
            )
        },
    },
}
</script>

<style lang="sass">
.template-link
    padding: 5px
    border-bottom: 1px solid $theme-dark-grey
    cursor: pointer
    vertical-align: middle
    svg
        margin-top: 3px
    .max-one-line
        width: calc(100% - 2em)
    .edit-icon
        margin-top: 4px
    .edit-icon, .trash-icon
        width: 0px
        visibility: hidden
    &:hover
        background-color: $theme-dark-grey
        .max-one-line
            width: calc(100% - 5em)
        .edit-icon, .trash-icon
            visibility: visible
            width: auto
    &.active
        background-color: $theme-dark-grey
</style>
