<template>
    <div class="category-select">
        <multiselect
            label="name"
            trackBy="id"

            :placeholder="placeholder"
            :value="value"
            :options="options"

            :maxHeight="500"
            :multiple="true"
            :showLabels="false"
            :searchable="false"
            :allow-empty="true"
            :hide-selected="true"
            :clear-on-select="false"
            :close-on-select="false"

            @input="newValue => $emit('input', newValue)"
            @select="(selectedOption, id) => $emit('select', selectedOption, id)"
            @remove="(removedOption, id) => $emit('remove', removedOption, id)"
        >
            <template
                slot="tag"
                slot-scope="{ option, remove }"
            >
                <category-tag
                    class="mb-1"
                    :category="option"
                    :removable="true"
                    @remove-category="remove(option)"
                />
            </template>

            <template
                slot="option"
                slot-scope="{ option }"
            >
                <category-tag
                    :category="option"
                    :removable="false"
                />
            </template>
        </multiselect>
    </div>
</template>

<script>
import CategoryTag from '@/components/category/CategoryTag.vue'

import multiselect from 'vue-multiselect'

export default {
    components: {
        CategoryTag,
        multiselect,
    },
    props: {
        options: {
            required: true,
        },
        value: {
            required: true,
        },
        placeholder: {
            default: 'Filter By Category',
        },
    },
}
</script>

<style src="vue-multiselect/dist/vue-multiselect.min.css"></style>

<style lang="sass">
@import '~sass/partials/shadows.sass'

.category-select .multiselect
    @extend .theme-shadow
    border-radius: 5px

    .multiselect__content-wrapper
        @extend .theme-shadow

    .multiselect__placeholder
        color: $theme-dark-blue

    span.multiselect__option--highlight
        background: $theme-medium-grey
</style>
