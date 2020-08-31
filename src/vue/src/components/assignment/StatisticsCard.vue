<template>
    <b-card
        :class="$root.getBorderClass($route.params.cID)"
        class="no-hover"
    >
        <div class="multi-form">
            <b>Needs marking</b>
            <number-badge
                :badges="[{ value: stats.needsMarking }]"
                :absolute="false"
                keyPrefix="needs-marking-statistics"
                class="float-right"
            />
        </div>
        <div class="multi-form">
            <b>Unpublished grades</b>
            <number-badge
                :badges="[{ value: stats.unpublished }]"
                :absolute="false"
                class="float-right"
                keyPrefix="unpublished-grades-statistics"
            />
        </div>
        <div :class="{'multi-form': stats.importRequests > 0}">
            <b>Average points</b>
            <number-badge
                :badges="[{ value: stats.averagePoints }]"
                :absolute="false"
                class="float-right"
                keyPrefix="average-points-statistics"
            />
        </div>
        <div v-if="stats.importRequests">
            <b>Import requests</b>
            <number-badge
                :badges="[{ value: stats.importRequests }]"
                :absolute="false"
                class="float-right"
                keyPrefix="average-points-statistics"
            />
        </div>
    </b-card>
</template>

<script>
import NumberBadge from '@/components/assets/NumberBadge.vue'

export default {
    components: {
        NumberBadge,
    },
    props: ['stats'],
}
</script>
