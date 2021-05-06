<template>
    <div style="overflow-x:auto;">
        <table class="rubric-read">
            <thead>
                <tr class="main-column-headers">
                    <th>Criteria</th>
                    <th>Levels</th>
                    <th>Score</th>
                </tr>
            </thead>

            <tbody>
                <tr
                    v-for="criterion in rubric.criteria"
                    :key="`criterion-${criterion.id}-row`"
                >
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

                    <td class="align-bottom score">
                        <b-form-input
                            class="inline"
                            type="number"
                            size="2"
                            placeholder="-"
                            disabled
                        />
                    </td>
                </tr>
            </tbody>

            <tfoot>
                <tr>
                    <td colspan="2"/>
                    <td>
                        <span class="oneline">Score: </span>
                    </td>
                </tr>
            </tfoot>
        </table>
    </div>
</template>

<script>
// import CriterionReadMode from '@/components/rubric/CriterionReadMode.vue'

export default {
    components: {
        // CriterionReadMode,
    },
    props: {
        rubric: {
            required: true,
            type: Object,
        },
    },
}
</script>

<style lang="sass">
%remove-default-table-styling
    margin: 0
    padding: 0
    border: 0
    font-size: 100%
    font: inherit
    vertical-align: top

.rubric-read
    & > table, caption, tbody, tfoot, thead, tr, th, td
        @extend %remove-default-table-styling

    & > table
        border-collapse: collapse
        border-spacing: 0

    th, td
        padding: 10px
        text-align: left
        border: 1px solid #ccc

    td:not(.score)
        min-width: 200px  // TODO Rubric table cell min width def

    .main-column-headers
        font-weight: bold

    .oneline
        white-space: nowrap

    .levels-cell-table-container  // Outer container where the levels table is nested
        padding: 0px
        height: 250px // We have to define the heigth for the nested table to scale its heigth relative to this

    .levels
        & > table
            height: 100%

        & > table, caption, tbody, tfoot, thead, tr, th, td
            border: 0

        .level-cell
            cursor: pointer
            &:hover
                background-color: $theme-light-grey
            &:not(:first-child)
                border-left: 1px solid #ccc
            &:not(:last-child)
                border-right: 1px solid #ccc
</style>
