<template>
    <b-card>
        <h3
            slot="header"
            class="theme-h3"
        >
            Statistics
        </h3>
        <div class="mb-2">
            Needs marking
            <number-badge
                :badges="[{ value: stats.needsMarking }]"
                :absolute="false"
                keyPrefix="needs-marking-statistics"
                class="float-right"
            />
        </div>
        <div class="mb-2">
            Unpublished grades
            <number-badge
                :badges="[{ value: stats.unpublished }]"
                :absolute="false"
                class="float-right"
                keyPrefix="unpublished-grades-statistics"
            />
        </div>
        <div :class="{'mb-2': stats.importRequests > 0}">
            Average points
            <number-badge
                :badges="[{ value: stats.averagePoints }]"
                :absolute="false"
                class="float-right"
                keyPrefix="average-points-statistics"
            />
        </div>
        <div v-if="stats.importRequests">
            Import requests
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
