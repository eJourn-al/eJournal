<template>
    <div
        ref="dropdown-button-wrapper"
        class="position-relative dropdown-button-wrapper"
    >
        <b-button
            :class="buttonClass"
            class="dropdown-button"
            @click="emitClick(selectedOption)"
        >
            <icon
                :name="options[selectedOption].icon"
                scale="1"
            />
            {{ options[selectedOption].text }}
            <span
                @click.prevent.stop="() => {
                    isOpen = !isOpen
                }"
            >
                <icon
                    v-if="isOpen"
                    name="caret-up"
                />
                <icon
                    v-else
                    name="caret-down"
                />
            </span>
        </b-button>
        <div
            v-if="isOpen"
            class="dropdown-button-options"
            :class="{ up: up }"
        >
            <b-button
                v-for="(details, option) in filteredOptions"
                :key="option"
                :class="details.class"
                class="option"
                @click="emitChangeOption(option)"
            >
                <icon
                    :name="details.icon"
                    scale="1"
                />
                {{ details.text }}
            </b-button>
        </div>
    </div>
</template>

<script>
export default {
    props: {
        selectedOption: {
            required: true,
        },
        options: {
            required: true,
        },
        up: {
            default: false,
        },
    },
    data () {
        return {
            isOpen: false,
        }
    },
    computed: {
        buttonClass () {
            return {
                [this.options[this.selectedOption].class]: true,
                active: this.isOpen,
            }
        },
        filteredOptions () {
            const filteredOptions = Object.assign({}, this.options)
            delete filteredOptions[this.selectedOption]

            return filteredOptions
        },
    },
    mounted () {
        this.$refs['dropdown-button-wrapper'].addEventListener('mouseleave', () => {
            this.isOpen = false
        })
    },
    methods: {
        emitClick (option) {
            this.isOpen = false
            this.$emit('click', option)
        },
        emitChangeOption (option) {
            this.isOpen = false
            this.$emit('change-option', option)
        },
    },
}

</script>

<style lang="sass">
@import '~sass/modules/colors.sass'
@import '~sass/partials/shadows.sass'

.dropdown-button-wrapper
    .dropdown-button
        z-index: 1
        span
            display: inline-block
            margin: 0px -0.375rem 0px 0.375rem
            padding: 0px 0.375rem
            border-radius: 5px !important
            border: 1px solid $theme-dark-grey
            background-color: rgba(0, 0, 0, 0.05)
            transition: all 0.3s cubic-bezier(.25,.8,.25,1) !important
            svg
                fill: grey !important
            &:hover
                background-color: rgba(0, 0, 0, 0.2)
        &:hover:not(.no-hover), &.active
            svg
                fill: white !important
            span.dropdown
                border-color: rgba(50, 50, 50, 0.2)

    .dropdown-button-options
        position: absolute
        top: 100%
        right: 0px
        @extend .theme-shadow
        background: $theme-medium-grey !important
        border: none !important
        border-radius: 0px 0px 5px 5px !important
        padding: 5px 5px 0px 5px
        &.up
            bottom: 100%
            top: auto
        .option
            justify-content: left
            text-align: left
            margin-bottom: 5px
            width: 100%
            line-height: 1.1em
            svg
                min-width: 0.95em
                margin-left: 0px
</style>
