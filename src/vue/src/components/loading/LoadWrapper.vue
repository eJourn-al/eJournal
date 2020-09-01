<template>
    <transition
        name="fade"
        mode="out-in"
    >
        <load-spinner
            v-if="showSpinner"
            class="mt-5"
        />
        <div v-else-if="!loading">
            <slot/>
        </div>
    </transition>
</template>

<script>
import loadSpinner from '@/components/loading/LoadSpinner.vue'

export default {
    components: {
        loadSpinner,
    },
    props: {
        loading: {
            required: true,
        },
        timeBeforeShow: {
            required: false,
            default: 1000,
        },
    },
    data () {
        return {
            keepSpinning: false,
            minTimePassed: false,
        }
    },
    computed: {
        showSpinner () {
            return (this.loading && this.minTimePassed) || this.keepSpinning
        },
    },
    created () {
        setTimeout(() => {
            if (this.loading) {
                this.keepSpinning = true
                this.minTimePassed = true
                setTimeout(() => {
                    this.keepSpinning = false
                }, 500)
            }
        }, this.timeBeforeShow)
    },
}
</script>
