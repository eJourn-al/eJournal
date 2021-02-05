<template>
    <div
        class="category-display"
        :class="{
            'compact': compact,
        }"
    >
        <category-tag
            v-for="category in categories"
            :key="`${id}-category-${category.id}`"
            :category="category"
            :removable="editable"
            :showInfo="true"
            @click.native="$emit('select-category', category)"
            @remove-category="$emit('remove-category', category)"
            @show-info="
                infoCategory = $event
                $nextTick(() => { $bvModal.show(infoModalID) })
            "
        />

        <slot/>

        <category-information-modal
            :id="infoModalID"
            :category="infoCategory"
        />
    </div>
</template>

<script>
import CategoryInformationModal from '@/components/category/CategoryInformationModal.vue'
import CategoryTag from '@/components/category/CategoryTag.vue'

export default {
    name: 'CategoryDisplay',
    components: {
        CategoryInformationModal,
        CategoryTag,
    },
    props: {
        categories: {
            required: true,
            type: Array,
        },
        id: {
            type: String,
            required: true,
        },
        editable: {
            default: false,
        },
        compact: {
            default: false,
        },
    },
    data () {
        return {
            infoCategory: null,
        }
    },
    computed: {
        infoModalID () { return `${this.id}-category-information` },
    },
}
</script>

<style lang="sass">
.category-display
    &.compact
        display: block
        width: auto
        max-width: 100%
        overflow-x: auto
        white-space: nowrap
        scrollbar-width: none
        &::-webkit-scrollbar
            display: none
        &:hover
            white-space: normal
        transition: height 0.3s cubic-bezier(.25,.8,.25,1) !important

</style>
