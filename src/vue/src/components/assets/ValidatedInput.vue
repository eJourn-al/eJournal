<template>
    <!-- eslint-disable vue/attribute-hyphenation -->
    <b-form-group
        :invalid-feedback="invalidFeedback"
        :state="state"
    >
        <b-form-input
            v-model="data"
            :placeholder="placeholder"
            type="text"
            trim
        />
    </b-form-group>
    <!-- eslint-enable vue/attribute-hyphenation -->
</template>

<script>
export default {
    props: {
        value: {
            required: true,
        },
        placeholder: {
            required: true,
            type: String,
        },
        /* NOTE: HTML supported, take care. */
        invalidFeedback: {
            required: true,
            type: String,
        },
        validator: {
            required: true,
        },
        validatorArgs: {
            type: Array,
            default: () => [],
        },
    },
    data () {
        return {
            state: null,
        }
    },
    computed: {
        data: {
            get () { return this.value },
            set (value) { this.$emit('input', value) },
        },
    },
    watch: {
        data (val) {
            this.state = this.validator(val, ...this.validatorArgs)
        },
    },
}
</script>
