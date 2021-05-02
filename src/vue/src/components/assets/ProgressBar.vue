<template>
    <div>
        <span class="progress-percentage">
            {{ progressPercentage }}%
        </span>
        <b>{{ currentPoints ? currentPoints : 0 }}</b> Points
        <tooltip
            v-if="bonusPoints != 0"
            :tip="`${currentPoints - bonusPoints} journal point${Math.abs(currentPoints - bonusPoints) !== 1 ? 's'
                : ''} + ${bonusPoints} bonus point${Math.abs(bonusPoints) !== 1 ? 's' : ''}`"
        />
        <b-progress
            :max="totalPoints"
            class="progress-bar-box mb-1"
            color="white"
        >
            <template v-if="comparePoints === -1">
                <b-progress-bar
                    :value="currentPoints"
                    class="first-bar"
                />
            </template>
            <template v-else-if="currentPoints < comparePoints">
                <b-progress-bar
                    :value="currentPoints"
                    class="first-bar"
                />
                <b-progress-bar
                    :value="Math.min(totalPoints, comparePoints) - currentPoints"
                    class="compare-bar"
                />
            </template>
            <template v-else>
                <b-progress-bar
                    :value="comparePoints"
                    class="first-bar"
                />
                <b-progress-bar
                    :value="Math.min(totalPoints, currentPoints) - comparePoints"
                    class="compare-bar ahead"
                />
            </template>
        </b-progress>
        <small v-if="bonusPoints != 0">
            <icon
                name="star"
                scale="0.8"
                class="fill-orange shift-up-2 mr-1"
            />
            <b>{{ bonusPoints }}</b> bonus point{{ Math.abs(bonusPoints) !== 1 ? "s" : "" }}
            <br/>
        </small>
        <small v-if="comparePoints >= 0">
            <icon
                :class="compareClass"
                name="signal"
                scale="0.8"
                class="shift-up-2"
            />
            {{ message }}
        </small>
    </div>
</template>

<script>
import tooltip from '@/components/assets/Tooltip.vue'

export default {
    components: {
        tooltip,
    },
    props: {
        currentPoints: {
            required: true,
        },
        totalPoints: {
            required: true,
        },
        comparePoints: {
            default: -1,
        },
        bonusPoints: {
            default: 0,
        },
    },
    computed: {
        progressPercentage () {
            return this.zeroIfNull((this.currentPoints * 100) / this.totalPoints).toFixed(0)
        },
        difference () {
            return Math.round(Math.abs((this.comparePoints - this.currentPoints) * 100)) / 100
        },
        message () {
            if (this.comparePoints === -1) {
                return null
            }
            let message = ''

            // On average
            if (this.difference === 0) {
                message += 'Same as average'
            } else {
                if (this.difference === 1) {
                    message += '1 point '
                } else {
                    message += `${this.difference} points `
                }
                // Ahead or behind
                if (this.comparePoints <= this.currentPoints) {
                    message += 'above average'
                } else {
                    message += 'below average'
                }
            }
            return message
        },
        compareClass () {
            if (this.difference === 0) {
                return 'fill-grey'
            } else if (this.comparePoints <= this.currentPoints) {
                return 'fill-green'
            }

            return 'fill-orange'
        },
    },
    methods: {
        zeroIfNull (val) {
            return !val ? 0 : val
        },
    },
}
</script>

<style lang="sass">
.progress-percentage
    float: right
    color: $theme-blue
    font-weight: bold

.progress.progress-bar-box
    height: 10px
    background-color: $theme-light-grey
    border: 1px solid $border-color
    border-radius: 5px !important

.first-bar
    background-color: $theme-blue !important
.compare-bar
    background-color: $theme-orange !important
    &.ahead
        background-color: $theme-green !important
</style>
