<template>
    <b-badge
        v-if="category.name"
        class="category-tag"
        :style="`background-color: ${category.color}`"
        pill
        @click="$emit('select-category', category)"
    >
        {{ category.name }}
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
</style>
