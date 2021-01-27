<!-- TODO: update and replace all (single) selection fields. -->
<template>
    <multiselect
        :value="value"
        :label="label"
        :trackBy="trackBy ? trackBy : label"
        :maxHeight="500"
        :class="{
            'multiple': multiple,
            'force-show-placeholder': !isOpen && (!value || !value.length),
            'show-search': isOpen && searchable,
            'show-limit': value && value.length,
        }"
        :options="sortedOptions"
        :multiple="multiple"
        :limit="multiple ? -1 : 1"
        :closeOnSelect="!multiple"
        :clearOnSelect="false"
        :preselectFirst="false"
        :searchable="searchable"
        :preserveSearch="false"
        :showLabels="false"
        :placeholder="(!multiple && value) ? value[label] : placeholder"
        class="theme-multiselect theme-select"
        open-direction="bottom"
        @input="newValue => $emit('input', newValue)"
        @select="(selectedOption, id) => $emit('select', selectedOption, id)"
        @remove="(removedOption, id) => $emit('remove', removedOption, id)"
        @open="() => { isOpen = true }"
        @close="() => { isOpen = false }"
    >
        <span slot="limit">
            {{ (value && value.length) ? value.length : 'No' }} {{ multiSelectText }}
        </span>
        <template slot="placeholder">
            {{ placeholder }}
        </template>
        <template slot="noResult">
            Not found
        </template>
    </multiselect>
</template>

<script>
import multiselect from 'vue-multiselect'

export default {
    components: {
        multiselect,
    },
    props: {
        options: {
            required: true,
        },
        value: { // Used by v-model.
            required: true,
        },
        label: {
            required: true,
        },
        trackBy: {
            required: true,
        },
        placeholder: {
            default: 'Click to select',
        },
        multiple: {
            default: false,
        },
        searchable: {
            default: false,
        },
        multiSelectText: {
            default: 'selected',
        },
    },
    data () {
        return {
            isOpen: false,
        }
    },
    computed: {
        sortedOptions () {
            if (!Array.isArray(this.options)) return []

            const optionsCopy = this.options.slice()
            return optionsCopy.sort((option1, option2) => {
                const selected1 = Array.isArray(this.value) && this.value.includes(option1)
                const selected2 = Array.isArray(this.value) && this.value.includes(option2)
                if (selected1 && !selected2) return -1
                if (!selected1 && selected2) return 1
                if (option1.name < option2.name) return -1
                return 1
            })
        },
    },
}
</script>

<style lang="sass">
@import '~sass/partials/shadows.sass'

div.theme-multiselect
    color: $theme-dark-blue
    box-sizing: border-box
    .multiselect__tags
        padding-left: 12px
        cursor: default
        font-size: 1em
        border-radius: 5px
        border-width: 0px
        white-space: nowrap
        overflow: hidden
        span
            display: none
        .multiselect__placeholder, .multiselect__single
            display: block
            color: inherit
            font-size: inherit
            line-height: inherit
            margin: 0px
            padding: 0px
        .multiselect__tags-wrap
            display: none
        .multiselect__placeholder
            text-transform: capitalize
    &.no-right-radius
        .multiselect__tags
            border-top-right-radius: 0 !important
            border-bottom-right-radius: 0 !important
    &.show-limit .multiselect__tags span:not(.multiselect__single)
        display: inline-block
    &.show-search.multiple .multiselect__tags
        font-size: 0.8em
        span
            display: inline-block
            position: relative
        input
            background: rgba(0, 0, 0, 0)
            position: relative
            display: block
            top: -2px
            left: -4px
    &.multiple
        .multiselect__single
            display: none
    .multiselect__select
        &::before
            border-color: $theme-dark-blue transparent transparent
    .multiselect__content-wrapper
        @extend .theme-shadow
        left: 0px
        border-radius: 0px 0px 5px 5px !important
    &.force-show-placeholder
        .multiselect__placeholder
            display: block
    &.multiselect--active .multiselect__tags
        max-height: 1.575em
        border-radius: 5px 5px 0px 0px
    span.multiselect__option--selected, span.multiselect__option--selected::after
        background: $theme-light-grey !important
        color: $theme-dark-blue
    span.multiselect__option--selected::before
        content: '\2022'
        font-size: 2em
        line-height: 10px
        vertical-align: middle
        margin-right: 4px
        color: $theme-blue
    span.multiselect__option--highlight, span.multiselect__option--highlight::after
        background: $theme-medium-grey !important
        color: $theme-dark-blue
</style>

<style src="vue-multiselect/dist/vue-multiselect.min.css"></style>
