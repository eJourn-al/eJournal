<template>
    <transition
        name="fade"
        mode="out-in"
    >
        <load-spinner v-if="showSpinner"/>
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
    },
    data () {
        return {
            keepSpinning: false,
        }
    },
    computed: {
        showSpinner () {
            return this.loading || this.keepSpinning
        },
    },
    created () {
        setTimeout(() => {
            if (this.loading) {
                this.keepSpinning = true
                setTimeout(() => {
                    this.keepSpinning = false
                }, 500)
            }
        }, 1000)
    },
}
</script>
