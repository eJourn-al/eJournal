<template>
    <div class="category-select">
        <multiselect
            ref="categorySelect"
            label="name"
            trackBy="id"
            class="theme-shadow"
            :open-direction="openDirection"

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
            :max="options.length"

            @input="newValue => $emit('input', newValue)"
            @select="(selectedOption, id) => $emit('select', selectedOption, id)"
            @remove="(removedOption, id) => $emit('remove', removedOption, id)"
            @close="(value, id) => $emit('close', value, id)"
        >
            <template
                slot="tag"
                slot-scope="{ option, remove }"
            >
                <category-tag
                    class="mb-1"
                    :showInfo="true"
                    :category="option"
                    :removable="true"
                    @remove-category="remove(option)"
                    @show-info="
                        infoCategory = $event
                        $nextTick(() => { $bvModal.show(infoModalID) })
                    "
                />
            </template>

            <template
                slot="option"
                slot-scope="{ option }"
            >
                <div :id="`category-${option.id}-option-wrapper`">
                    <category-tag
                        :category="option"
                        :removable="false"
                        :showInfo="true"
                        @show-info="showCategoryDescriptionInSelectOptions"
                    />
                    <template v-if="descriptionCategory === option">
                        <br/>
                        <sandboxed-iframe
                            class="mt-2"
                            :content="option.description"
                        />
                    </template>
                </div>
            </template>

            <template
                slot="maxElements"
            >
                No more categories.
            </template>
        </multiselect>

        <category-information-modal
            :id="infoModalID"
            :category="infoCategory"
        />
    </div>
</template>

<script>
import CategoryInformationModal from '@/components/category/CategoryInformationModal.vue'
import CategoryTag from '@/components/category/CategoryTag.vue'
import SandboxedIframe from '@/components/assets/SandboxedIframe.vue'

import multiselect from 'vue-multiselect'

export default {
    components: {
        CategoryInformationModal,
        CategoryTag,
        multiselect,
        SandboxedIframe,
    },
    props: {
        options: {
            required: true,
        },
        value: {
            required: true,
        },
        openDirection: {
            default: 'bottom',
            type: String,
        },
        placeholder: {
            default: 'Filter By Category',
            type: String,
        },
        startOpen: {
            default: false,
            type: Boolean,
        },
    },
    data () {
        return {
            descriptionCategory: null,
            infoCategory: null,
            optionsDropdownSize: null,
        }
    },
    computed: {
        /* Makes use of random to enable multiple selects as part of the same dom without forcing an id prop. */
        infoModalID () { return `${Math.random()}-category-select-information-modal` },
    },
    mounted () {
        if (this.startOpen) {
            this.$refs.categorySelect.$el.focus()
        }
    },
    methods: {
        showCategoryDescriptionInSelectOptions (category) {
            this.descriptionCategory = (this.descriptionCategory === category) ? null : category

            /* Scroll the option including description into view, nextTick is required due to the delayed scaling of
             * of the sandbox */
            this.$nextTick(() => {
                const el = this.$refs.categorySelect.$el.querySelector(`#category-${category.id}-option-wrapper`)

                if (el) {
                    el.scrollIntoView({ behavior: 'smooth', block: 'center' })
                }
            })
        },
    },
}
</script>

<style src="vue-multiselect/dist/vue-multiselect.min.css"></style>

<style lang="sass">
.category-select .multiselect
    color: $text-color
    word-wrap: nowrap !important
    &, .multiselect__content-wrapper
        border: 1px solid $border-color
    &, .multiselect__content-wrapper, .multiselect__tags
        border-radius: 5px !important
        .multiselect__placeholder, .multiselect__single
            color: inherit
    .multiselect__tags
        font-size: 1em
        border-width: 0px
    .multiselect__select::before
        border-color: $text-color transparent transparent
    span.multiselect__option--selected, span.multiselect__option--selected::after,
    span.multiselect__option--highlight, span.multiselect__option--highlight::after
        background: $theme-light-grey !important
        color: $text-color
</style>
