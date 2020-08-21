<template>
    <b-card
        :class="$root.getBorderClass($route.params.cID)"
        class="no-hover"
    >
        <div class="multi-form">
            <b>Needs marking</b><number-badges-display
                :badges="[{ value: stats.needsMarking }]"
                :absolute="false"
                keyPrefix="needs-marking-statistics"
                class="float-right"
            />
        </div>
        <div class="multi-form">
            <b>Unpublished grades</b><number-badges-display
                :badges="[{ value: stats.unpublished }]"
                :absolute="false"
                class="float-right"
                keyPrefix="unpublished-grades-statistics"
            />
        </div>
        <div>
            <b>Average points</b><number-badges-display
                :badges="[{ value: stats.averagePoints }]"
                :absolute="false"
                class="float-right"
                keyPrefix="average-points-statistics"
            />
        </div>
    </b-card>
</template>

<script>
import numberBadgesDisplay from '@/components/assets/NumberBadgesDisplay.vue'

export default {
    components: {
        numberBadgesDisplay,
    },
    props: ['stats'],
}
</script>
