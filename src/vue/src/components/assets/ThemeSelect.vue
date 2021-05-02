<!-- TODO: update and replace all (single) selection fields. -->
<template>
    <multiselect
        :value="value"
        :label="label"
        :trackBy="trackBy ? trackBy : label"
        :maxHeight="500"
        :options="sortedOptions"
        :multiple="multiple"
        :closeOnSelect="!multiple"
        :clearOnSelect="false"
        :preselectFirst="false"
        :searchable="searchable"
        :preserveSearch="false"
        :showLabels="false"
        :placeholder="(!multiple && value) ? value[label] : placeholder"
        class="theme-multiselect"
        open-direction="bottom"
        @input="newValue => $emit('input', newValue)"
        @select="(selectedOption, id) => $emit('select', selectedOption, id)"
        @remove="(removedOption, id) => $emit('remove', removedOption, id)"
    >
        <template slot="tag">
            {{ '' }}
        </template>
        <template slot="placeholder">
            {{ placeholder }}
        </template>
        <template slot="noResult">
            Not found
        </template>
        <template
            slot="selection"
            slot-scope="{ values, search, isOpen }"
        >
            <span
                v-if="values.length && !isOpen"
                class="multiselect__single"
            >
                <template v-if="showCount">
                    {{ values.length }}
                </template>
                {{ multiSelectText }}
            </span>
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
        showCount: {
            default: true,
        },
        multiSelectText: {
            default: 'selected',
        },
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

<style src="vue-multiselect/dist/vue-multiselect.min.css"></style>
<style lang="sass">

div.theme-multiselect
    color: $text-color
    word-wrap: nowrap !important
    border-radius: 5px
    &, .multiselect__content-wrapper
        border: 1px solid $border-color
    &, .multiselect__content-wrapper, .multiselect__tags
        border-radius: 5px !important
    &.no-right-radius
        border-top-right-radius: 0 !important
        border-bottom-right-radius: 0 !important
    .multiselect__tags
        font-size: 1em
        border-width: 0px
        input
            padding: 0px !important
            margin-bottom: 0px
            &:focus
                border-width: 0px
        input, span
            display: block
            width: auto
            max-width: 100%
            text-overflow: ellipsis
            white-space: nowrap
            overflow: hidden
        .multiselect__placeholder, .multiselect__single
            color: inherit
        .multiselect__placeholder
            padding-top: 0px
            margin-bottom: 0px
    .multiselect__select::before
        border-color: $text-color transparent transparent
    span.multiselect__option--selected, span.multiselect__option--selected::after,
    span.multiselect__option--highlight, span.multiselect__option--highlight::after
        background: $theme-light-grey !important
        color: $text-color
    span.multiselect__option--selected::before
        content: '\2022'
        font-size: 2em
        line-height: 10px
        vertical-align: middle
        margin-right: 4px
        color: $theme-blue
</style>
