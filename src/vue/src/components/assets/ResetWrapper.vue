<template>
    <div class="reset-wrapper">
        <slot/>
        <b-button
            v-if="value"
            class="red-button reset-button float-right"
            @click="$emit('input', null)"
        >
            <icon name="trash"/>
        </b-button>
    </div>
</template>

<script>
export default {
    props: {
        value: { // Used by v-model.
            required: true,
        },
    },
}
</script>

<style lang="sass">
.reset-wrapper
    position: relative
    .btn.reset-button
        position: absolute
        right: 5px
        top: 5px
        padding: 0
        opacity: 0
        transition: all 0.3s cubic-bezier(.25,.8,.25,1)
    &:hover .reset-button
        opacity: 1
</style>
