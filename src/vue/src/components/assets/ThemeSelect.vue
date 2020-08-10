<!-- TODO: update and replace all (single) selection fields. -->
<template>
    <!-- eslint-disable vue/attribute-hyphenation -->
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
        open-direction="bottom"
        @input="newValue => $emit('input', newValue)"
        @open="() => { isOpen = true }"
        @close="() => { isOpen = false }"
        @select="(selectedOption, id) => $emit('select', (selectedOption, id))"
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
        <icon
            slot="caret"
            name="sort"
            scale="0.8"
            class="caret multiselect__caret"
        />
    </multiselect>
    <!-- eslint-enable vue/attribute-hyphenation -->
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
@import '~sass/modules/colors.sass'
@import '~sass/modules/breakpoints.sass'
@import '~sass/partials/shadows.sass'

.multiselect
    color: $theme-dark-blue
    .multiselect__tags
        @extend .theme-shadow
        -moz-user-select: -moz-none
        -khtml-user-select: none
        -webkit-user-select: none
        -o-user-select: none
        user-select: none
        position: relative
        cursor: default
        font-family: 'Roboto Condensed', sans-serif
        font-size: 1.1em
        border-radius: 5px
        border: 1px solid $theme-dark-grey
        padding: 0.375rem 0.75rem
        z-index: 20
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
    &:not(.multiple) .multiselect__tags .multiselect__input
        font-size: inherit
        line-height: inherit
        margin: 0px
        padding: 0px
    &.no-right-radius
        .multiselect__tags
            border-top-right-radius: 0 !important
            border-bottom-right-radius: 0 !important
    &.show-limit .multiselect__tags span
        display: inline-block
    &.show-search.multiple .multiselect__tags
        font-size: 1em
        span
            display: inline-block
            position: relative
            top: 4px
            font-size: 0.8em
        input
            background: rgba(0, 0, 0, 0)
            position: relative
            display: block
            top: -2px
            left: -4px
            font-family: 'Roboto Condensed', sans-serif
    &.multiple
        .multiselect__single
            display: none
    .multiselect__select::before
        border-color: $theme-dark-blue transparent transparent
    .multiselect__content-wrapper
        @extend .theme-shadow
        font-family: 'Roboto Condensed', sans-serif
        font-size: 1.2em
        background-color: white
        z-index: 1
        border-radius: 0px 0px 5px 5px !important
        padding-top: 10px
        transform: translateY(-10px)
    &.force-show-placeholder
        .multiselect__placeholder
            display: block
    .multiselect__caret
        position: absolute
        right: 10px
        z-index: 21
        top: 50%
        transform: translateY(-50%)
    &.multiselect--active
        .multiselect__tags
            box-shadow: 0 3px 6px rgba(0,0,0,0.16), 0 3px 6px rgba(0,0,0,0.23) !important
            max-height: 1.575em
    &.multiselect--above
        .multiselect__content-wrapper
            border-radius: 5px 5px 0px 0px !important
            padding-bottom: 10px
            padding-top: 0px
            transform: translateY(10px)
    span.multiselect__option--highlight, span.multiselect__option--highlight::after
        background: $theme-medium-grey !important
        color: $theme-dark-blue
    .multiselect__option--selected
        font-weight: 400
    .multiselect__option--selected::before
        content: "•"
        margin-right: 10px
        margin-left: -5px
        font-size: 1.5em
        vertical-align: middle
        font-weight: bold
        color: $theme-green
</style>

<style src="vue-multiselect/dist/vue-multiselect.min.css"></style>
