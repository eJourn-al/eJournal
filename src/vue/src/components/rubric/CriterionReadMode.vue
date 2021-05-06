<template>
    <div colspan="1">
        <td class="criterion-cell">
            <p class="oneline">
                <b>{{ criterion.name }}</b>
            </p>

            <p>
                {{ criterion.description }}
            </p>
        </td>

        <td class="levels-cell-table-container">
            <table
                class="levels"
                style="height: 100%"
            >
                <tbody>
                    <tr>
                        <td
                            v-for="level in criterion.levels"
                            :key="`criterion-${criterion.id}-level-${level.id}`"
                            class="level-cell"
                        >
                            <p class="oneline">
                                <b>{{ level.name }}</b>
                            </p>

                            <p class="oneline">
                                <b>Score</b>: {{ level.points }}
                            </p>

                            <p>
                                {{ level.description }}
                            </p>
                        </td>
                    </tr>
                </tbody>
            </table>
        </td>

        <td class="align-bottom">
            <b-form-input
                v-if="selectedLevel"
                v-model="selectedLevel.points"
                class="inline"
                type="number"
                size="2"
                placeholder="-"
                min="0.0"
                :formatter="floatFormatter"
            />
            <b-form-input
                v-else
                class="inline"
                type="number"
                size="2"
                placeholder="-"
                disabled
            />
        </td>
    </div>
</template>

<script>
export default {
    props: {
        rubric: {
            required: true,
            type: Object,
        },
        criterion: {
            required: true,
            type: Object,
        },
    },
    data () {
        return {
            selectedLevel: null,
        }
    },
    computed: {
        maxPoints () {
            return Math.max(...this.criterion.levels.map((level) => level.points))
        },
    },
    methods: {
        floatFormatter (value) {
            if (value === '') { return 0 }
            return parseFloat(value)
        },
    },
}
</script>

<style>

</style>
