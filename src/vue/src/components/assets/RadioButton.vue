<template>
    <div class="theme-radio-button text-nowrap">
        <b-button
            v-for="option in options"
            :key="`radio-button-${option.value}`"
            :class="[{ 'active': value == option.value }, option.class]"
            class="radio-button-option"
            @click="$emit('input', option.value)"
        >
            <icon :name="option.icon"/>
        </b-button>
    </div>
</template>

<script>
export default {
    props: {
        options: {
            required: true,
        },
        value: { // Used by v-model.
            required: true,
        },
    },
}
</script>

<style lang="sass">
.theme-radio-button
    border-radius: 5px
    .btn.radio-button-option, .btn-secondary.radio-button-option
        position: relative
        border-radius: 0px
        color: $text-color
        svg
            fill: $text-color
        &:hover, &.active, &:hover:not(.no-hover)
            svg
                fill: white
        &:first-child
            border-radius: 5px 0px 0px 5px
        &:last-child
            border-radius: 0px 5px 5px 0px

</style>
