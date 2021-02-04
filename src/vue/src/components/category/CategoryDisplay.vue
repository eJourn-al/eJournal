<template>
    <div
        :ref="`${id}-category-display`"
        :class="{
            'compact': compact,
        }"
        class="category-display"
    >
        <icon
            v-if="categories.length > 0"
            name="caret-left"
            class="category-left"
            @click.native="scrollLeft"
        />
        <category-tag
            v-for="category in categories"
            :key="`${id}-category-${category.id}`"
            :ref="`${id}-category-${category.id}`"
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
        <icon
            v-if="categories.length > 0"
            class="category-right"
            name="caret-right"
            @click.native="scrollRight"
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
    methods: {
        scrollLeft () {
            this.$refs[`${this.id}-category-display`].scrollBy({
                left: -this.$refs[`${this.id}-category-display`].clientWidth,
                behavior: 'smooth',
            });
        },
        scrollRight () {
            // Scroll to a certain element
            this.$refs[`${this.id}-category-display`].scrollBy({
                left: this.$refs[`${this.id}-category-display`].clientWidth,
                behavior: 'smooth',
            });
        },
    },
}
</script>

<style lang="sass">
.category-display
    .category-left, .category-right
        display: none
    &.compact
        display: block
        width: auto
        max-width: 100%
        overflow-x: scroll
        white-space: nowrap
        scrollbar-width: none
        scroll-behavior: smooth
        .category-left, .category-right
            position: absolute
            top: 50%
            transform: translateY(-50%)
            display: block
            color: $theme-medium-grey
            transition: all 0.3s cubic-bezier(.25,.8,.25,1)
            &:hover
                color: grey
                cursor: pointer
        .category-left
            left: 0px
        .category-right
            right: 0px
        &::-webkit-scrollbar
            display: none
</style>
