<template>
    <div>
        <h4 class="theme-h4 mb-2 mt-4">
            <span>Grading</span>
        </h4>
        <b-card
            :class="$root.getBorderClass($route.params.uID)"
            class="no-hover multi-form"
        >
            <div class="clearfix multi-form">
                <radio-button
                    v-model="$store.getters['preferences/saved'].auto_select_ungraded_entry"
                    :options="[
                        {
                            value: true,
                            icon: 'check',
                            class: 'add-button',
                        },
                        {
                            value: false,
                            icon: 'times',
                            class: 'delete-button',
                        },
                    ]"
                    class="float-right"
                    @input="e => $store.commit('preferences/CHANGE_PREFERENCES', { auto_select_ungraded_entry: e })"
                />
                <h2 class="theme-h2 field-heading">
                    Auto-select first ungraded entry
                    <tooltip
                        tip="Automatically select the first ungraded entry upon viewing a journal or submitting a grade"
                    />
                </h2>
            </div>

            <div class="clearfix">
                <radio-button
                    v-model="$store.getters['preferences/saved'].auto_proceed_next_journal"
                    :options="[
                        {
                            value: true,
                            icon: 'check',
                            class: 'add-button',
                        },
                        {
                            value: false,
                            icon: 'times',
                            class: 'delete-button',
                        },
                    ]"
                    class="float-right"
                    @input="e => $store.commit('preferences/CHANGE_PREFERENCES', { auto_proceed_next_journal: e })"
                />
                <h2 class="theme-h2 field-heading">
                    Automatically proceed to next journal
                    <tooltip
                        tip="Automatically proceed to the next journal once all entries in a journal are graded"
                    />
                </h2>
            </div>
        </b-card>
    </div>
</template>

<script>
import RadioButton from '@/components/assets/RadioButton.vue'
import tooltip from '@/components/assets/Tooltip.vue'

export default {
    components: {
        RadioButton,
        tooltip,
    },
    props: ['userData'],
}
</script>
