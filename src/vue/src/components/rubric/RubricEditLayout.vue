<template>
    <b-table-simple>
        <caption>
            Caption for the table, desired?
        </caption>

        <b-thead head-variant="dark">
            <b-tr>
                <b-th
                    colspan="12"
                >
                    <!-- {{ rubric.name }} -->
                    <b-form-group
                        style="max-width: 280px"
                    >
                        <b-form-input
                            v-model="rubric.name"
                            placeholder="Name"
                            type="text"
                            trim
                            required
                        />
                    </b-form-group>
                </b-th>
            </b-tr>

            <b-tr>
                <b-th>Criteria</b-th>
                <b-th>Levels</b-th>
                <b-th>Score</b-th>
            </b-tr>
        </b-thead>
    </b-table-simple>
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

<style>

</style>
