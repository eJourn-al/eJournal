<template>
    <div class="rubric-read">
        <table>
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
                        <table class="levels">
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

                    <td class="align-bottom score-cell">
                        <b-form-input
                            v-if="$hasPermission('can_grade')"
                            class="inline"
                            type="number"
                            size="2"
                            placeholder="-"
                            disabled
                        />
                        <span v-else>TODO RUBRIC: Display criterion grade</span>
                    </td>
                </tr>
            </tbody>

            <tfoot>
                <tr>
                    <td colspan="2"/>
                    <td class="score-cell">
                        <span class="oneline">Score: </span>
                    </td>
                </tr>
            </tfoot>
        </table>
    </div>
</template>

<script>

export default {
    props: {
        rubric: {
            required: true,
            type: Object,
        },
    },
}
</script>

<style lang="sass">
@import '~sass/partials/rubric.sass'

.rubric-read
    overflow-x: auto

    & > table, caption, tbody, tfoot, thead, tr, th, td
        @extend %remove-default-table-styling

    th, td
        padding: $cell-padding
        text-align: left
        border: $default-border

    td:not(.score-cell)
        min-width: $min-cell-width

    .main-column-headers
        font-weight: bold

    .oneline
        white-space: nowrap

    & > table
        border-collapse: collapse
        border-spacing: 0

        & > tbody > tr > td.levels-cell-table-container  // Outer container where the levels table is nested
            padding: 0px
            height: 250px // We have to define the heigth for the nested table to scale its heigth relative to this

            & > table.levels
                height: 100%

                & > tbody > tr
                    & > td, th
                        border: 0
                    & > td:not(:first-child)
                        border-left: $default-border
                    & > td:not(:last-child)
                        border-right: $default-border
</style>
