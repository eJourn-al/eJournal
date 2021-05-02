<template>
    <b-badge
        v-if="category.name"
        class="category-tag"
        :style="`background-color: ${category.color}`"
        pill
    >
        {{ category.name }}

        <icon
            v-if="showInfo && category.description"
            class="category-information-icon shift-up-3"
            name="info-circle"
            scale="0.8"
            @click.native.stop="$emit('show-info', category)"
        />

        <icon
            v-if="removable"
            class="category-tag__remove ml-1 shift-up-3"
            name="times"
            scale="0.8"
            @click.stop.native="$emit('remove-category', category)"
        />
    </b-badge>
</template>

<script>
export default {
    name: 'CategoryTag',
    props: {
        category: {
            required: true,
            type: Object,
        },
        removable: {
            default: false,
        },
        showInfo: {
            default: false,
        },
    },
}
</script>

<style lang="sass">
    .category-tag
        user-select: none
        &:not(:last-child)
            margin-right: 4px
        svg
            opacity: 0.5
            cursor: pointer
            &:hover
                opacity: 1
</style>
