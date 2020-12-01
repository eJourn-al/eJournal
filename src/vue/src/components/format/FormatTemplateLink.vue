<!--
    Used in a card in the format editor to open template editor, toggle availability, delete templates from pool.
-->

<template>
    <div
        class="template-link unselectable"
        @click="$emit('edit-template')"
    >
        <icon
            v-if="template.preset_only"
            v-b-tooltip:hover="'This template can only be used for preset entries you add to the timeline'"
            name="lock"
            class="fill-red float-right ml-2"
            @click.native.stop="togglePresetOnly"
        />
        <icon
            v-else
            v-b-tooltip:hover="'This template can be freely used by students as often as they want'"
            name="unlock"
            class="fill-green float-right ml-2"
            @click.native.stop="togglePresetOnly"
        />
        <icon
            name="trash"
            class="trash-icon ml-2 float-right"
            @click.native.stop="emitDeleteTemplate"
        />
        <icon
            name="edit"
            class="edit-icon float-right"
        />
        <b
            v-if="template.name"
            class="max-one-line"
        >
            {{ template.name }}
        </b>
        <b
            v-else
            class="text-red"
        >
            Untitled template
        </b>
        <span class="max-one-line">
            <span
                v-for="field in template.field_set"
                :key="field.id"
            >
                {{ field.name }}
            </span>
        </span>
    </div>
</template>

<script>
export default {
    props: ['template'],
    methods: {
        emitDeleteTemplate () {
            if (window.confirm(
                `Are you sure you want to delete template "${this.template.name}" from this assignment?`)) {
                this.$emit('delete-template')
            }
        },
        togglePresetOnly () {
            this.template.preset_only = !this.template.preset_only
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
        .max-one-line
            width: calc(100% - 5em)
        .edit-icon, .trash-icon
            visibility: visible
            width: auto
</style>
