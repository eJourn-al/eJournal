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
            class="ml-1 category-information-icon"
            name="info-circle"
            @click.native.stop="$emit('show-info', category)"
        />

        <icon
            v-if="removable"
            class="fill-red category-tag__remove ml-1 "
            name="times"
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
            margin-right: 5px

    .category-tag__remove
        cursor: pointer

    .category-information-icon
        &:hover
            cursor: pointer
            fill: $theme-dark-grey !important
        &.help-cursor:hover
            cursor: help
</style>
