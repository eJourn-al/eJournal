<template>
    <b-table-simple
        responsive
        striped
        noSortReset
        sortBy="name"
        class="mt-2 mb-0"
    >
        <b-thead>
            <b-tr>
                <b-th>
                    Name
                </b-th>
                <b-th>
                    Username
                </b-th>
                <b-th>
                    Email
                </b-th>
                <b-th>
                    Status
                </b-th>
                <b-th/>
            </b-tr>
        </b-thead>
        <b-tbody>
            <b-tr>
                <b-td>
                    Engel Hamer
                </b-td>
                <b-td>
                    ehamer1
                </b-td>
                <b-td>
                    e.hamer@uva.nl
                </b-td>
                <b-td>
                    <icon
                        name="history"
                        class="text-yellow"
                    />
                </b-td>
                <b-td>
                    <icon
                        name="trash"
                        class="trash-icon"
                    />
                </b-td>
            </b-tr>
            <b-tr>
                <b-td>
                    Lars van Hijfte
                </b-td>
                <b-td>
                    lhijfte
                </b-td>
                <b-td>
                    l.vanhijfte@uva.nl
                </b-td>
                <b-td>
                    <icon
                        name="check"
                        class="text-green"
                    />
                </b-td>
                <b-td>
                    <icon
                        name="trash"
                        class="trash-icon"
                    />
                </b-td>
            </b-tr>
        </b-tbody>
    </b-table-simple>
</template>

<script>
// import adminAPI from '@/api/admin.js'

export default {
    data () {
        return {

        }
    },
    methods: {

    },
}
</script>
