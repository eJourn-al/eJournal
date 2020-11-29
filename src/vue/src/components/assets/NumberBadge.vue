<template>
    <div :class="{'absolute': absolute}">
        <b-badge
            v-for="(d, i) in displayedBadges"
            :key="`${keyPrefix}-badge-${i}`"
            v-b-tooltip.hover="('tooltip' in d.badge) ? tooltipToMsg(d.badge.tooltip, d.badge.value) : ''"
            pill
            :class="d.class"
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
                'background-blue',
                'background-dark-blue',
                'background-yellow',
                'background-pink',
                'background-purple',
                'background-green',
                'background-red',
                'background-orange',
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
                    result.push({ badge, class: this.colorsStyles[index % this.colorsStyles.length] })
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
.absolute
    position: absolute
    right: 0px
    top: 0px
</style>
