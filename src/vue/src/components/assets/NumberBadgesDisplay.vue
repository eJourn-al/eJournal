<template>
    <div
        :class="{'absolute': absolute}"
        class="number-badges-container"
    >
        <b-badge
            v-for="(d, i) in displayedBadges"
            :key="`${keyPrefix}-badge-${i}`"
            v-b-tooltip.hover="('tooltip' in d.badge) ? tooltipToMsg(d.badge.tooltip, d.badge.value) : ''"
            class="badge-part"
            :class="{
                'border-left': i == 0,
                'border-right': i == displayedBadges.length - 1,
            }"
            :style="{ ...d.styles }"
        >
            {{ d.badge.value ? Math.round(d.badge.value * 100) / 100 : 0 }}
        </b-badge>
    </div>
</template>

<script>
export default {
    props: {
        absolute: {
            default: true,
            type: Boolean,
        },
        displayZeroValues: {
            default: true,
            type: Boolean,
        },
        keyPrefix: {
            required: true,
        },
        badges: {
            required: true,
            type: Array,
            default: () => [{
                value: 0,
                tooltip: 'Tooltip msg',
            }],
            validator: badges => badges.every(badge => 'value' in badge),
        },
    },
    data () {
        return {
            colorsStyles: [
                { 'background-color': '#22648A' }, // $theme-blue
                { 'background-color': '#FFFFFF', color: '#252C39' },
                { 'background-color': '#252C39' }, // $theme-dark-blue
                { 'background-color': '#E8A723' }, // $theme-yellow
                { 'background-color': '#E64769' }, // $theme-pink
                { 'background-color': '#473E62' }, // $theme-purple
                { 'background-color': '#007E33' }, // $theme-green
                { 'background-color': '#CC0000' }, // $theme-red
                { 'background-color': '#FF8800' }, // $theme-orange
            ],
        }
    },
    computed: {
        displayedBadges () {
            const result = []

            /* Create a mapping from badge to color, keeping the colors mapped in order despite reverse and
             * zero not displayed value */
            this.badges.forEach((badge, index) => {
                if ((badge.value === 0 && this.displayZeroValues) || badge.value) {
                    result.push({ badge, styles: this.colorsStyles[index % this.colorsStyles.length] })
                }
            })

            /* Reverse so we grow the list from right to left */
            return result.reverse()
        },
    },
    methods: {
        tooltipToMsg (tooltip, n) {
            if (tooltip === 'needsMarking') { return this.needsMarkingTooltip(n) }
            if (tooltip === 'unpublished') { return this.unpublishedTooltip(n) }
            if (tooltip === 'importRequests') { return this.importRequestTooltip(n) }
            return tooltip
        },
        needsMarkingTooltip (n) {
            return `${n} ${(n > 1) ? 'entries' : 'entry'} need${(n === 1) ? 's' : ''} marking`
        },
        unpublishedTooltip (n) {
            return `${n} grade${(n > 1) ? 's' : ''} need${(n === 1) ? 's' : ''} to be published`
        },
        importRequestTooltip (n) {
            return `${n} outstanding journal import request${(n > 1) ? 's' : ''}`
        },
    },
}
</script>

<style lang="sass">
@import '~sass/modules/colors.sass'

.absolute
    position: absolute
    right: 0px
    top: 0px

.number-badges-container
    font-size: 1em
    .badge-part
        border-top: 1px solid $theme-dark-grey !important
        border-bottom: 1px solid $theme-dark-grey !important
        border-radius: 0px !important
        font-size: 1em
        &.border-left
            border-left: 1px solid $theme-dark-grey !important
            border-top-left-radius: 5px !important
            border-bottom-left-radius: 5px !important
        &.border-right
            border-right: 1px solid $theme-dark-grey !important
            border-top-right-radius: 5px !important
            border-bottom-right-radius: 5px !important
</style>
