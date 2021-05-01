<template>
    <div
        v-if="categories"
        class="category-display"
        :class="{
            'compact': compact,
        }"
    >
        <span
            v-if="categories.length > 0"
            class="category-left"
            @click="scrollLeft"
        >
            <icon
                name="angle-left"
                class="shift-up-2"
            />
        </span>
        <span
            v-if="categories.length > 0"
            class="category-right"
            @click="scrollRight"
        >
            <icon
                name="angle-right"
                class="shift-up-2"
            />
        </span>
        <div :ref="`${id}-category-display`">
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
        </div>
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
        position: relative
        &:hover
            span.category-left, span.category-right
                opacity: 0.8
        div
            width: auto
            max-width: 100%
            overflow-x: scroll
            white-space: nowrap
            scroll-behavior: smooth
            scrollbar-width: none
            z-index: 20
            &::-webkit-scrollbar
                display: none
            &:hover
        span.category-left, span.category-right
            z-index: 21
            opacity: 0
            position: absolute
            height: 100%
            background: white
            padding: 2px
            display: block
            color: grey
            transition: all 0.3s cubic-bezier(.25,.8,.25,1)
            cursor: pointer
            &:hover
                opacity: 1
        .category-left
            left: 0px
        .category-right
            right: 0px
</style>
