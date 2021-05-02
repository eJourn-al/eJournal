<template>
    <b-table-simple
        responsive
        class="mb-0 no-top-table-border round-border"
    >
        <b-tbody>
            <b-tr>
                <b-td>
                    Auto-select first ungraded entry<br/>
                    <span class="small">
                        Automatically select the first ungraded entry upon viewing a journal or submitting a grade.
                    </span>
                </b-td>
                <b-td>
                    <radio-button
                        v-model="$store.getters['preferences/saved'].auto_select_ungraded_entry"
                        :options="[
                            {
                                value: true,
                                icon: 'check',
                                class: 'green-button',
                            },
                            {
                                value: false,
                                icon: 'times',
                                class: 'red-button',
                            },
                        ]"
                        class="float-right"
                        @input="e => $store.commit(
                            'preferences/CHANGE_PREFERENCES', { auto_select_ungraded_entry: e })"
                    />
                </b-td>
            </b-tr>
            <b-tr>
                <b-td>
                    Automatically proceed to next journal<br/>
                    <span class="small">
                        Automatically proceed to the next journal once all entries in a journal are graded.
                    </span>
                </b-td>
                <b-td>
                    <radio-button
                        v-model="$store.getters['preferences/saved'].auto_proceed_next_journal"
                        :options="[
                            {
                                value: true,
                                icon: 'check',
                                class: 'green-button',
                            },
                            {
                                value: false,
                                icon: 'times',
                                class: 'red-button',
                            },
                        ]"
                        class="float-right"
                        @input="e => $store.commit(
                            'preferences/CHANGE_PREFERENCES', { auto_proceed_next_journal: e })"
                    />
                </b-td>
            </b-tr>
        </b-tbody>
    </b-table-simple>
</template>

<script>
import RadioButton from '@/components/assets/RadioButton.vue'

export default {
    components: {
        RadioButton,
    },
}
</script>
