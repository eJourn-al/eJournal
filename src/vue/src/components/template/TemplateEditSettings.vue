<template>
    <b-card class="no-hover">
        <radio-button
            v-model="template.preset_only"
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
            class="float-right mb-3 ml-3"
        />
        <h2 class="theme-h2 field-heading multi-form">
            Unlimited use
        </h2>
        Allow students to use this template for new entries in their journal.
        When disabled, this template can still be used for deadlines you add to the timeline.
        <template v-if="assignmentHasCategories">
            <hr/>
            <!-- TODO CATEGORY: Invert the notion of 'fixed categories' in the back end? This seems more natural. -->
            <radio-button
                v-model="template.fixed_categories"
                :options="[
                    {
                        value: false,
                        icon: 'check',
                        class: 'green-button',
                    },
                    {
                        value: true,
                        icon: 'times',
                        class: 'red-button',
                    },
                ]"
                class="float-right mb-3 ml-3"
            />
            <h2 class="theme-h2 field-heading multi-form">
                Allow custom categories
            </h2>
            Allow students to choose which categories they add to their entry when using this template.
            <hr/>
            <h2 class="theme-h2 field-heading">
                Default categories
            </h2>
            Select which categories are added to entries using this template by default.
            <category-select
                v-model="template.categories"
                class="mt-2"
                :options="assignmentCategories"
                :openDirection="'top'"
                placeholder="Set categories"
            />
        </template>
    </b-card>
</template>

<script>
import { mapGetters } from 'vuex'
import CategorySelect from '@/components/category/CategorySelect.vue'
import RadioButton from '@/components/assets/RadioButton.vue'

export default {
    name: 'TemplateEditSettings',
    components: {
        CategorySelect,
        RadioButton,
    },
    props: {
        template: {
            required: true,
            type: Object,
        },
    },
    computed: {
        ...mapGetters({
            assignmentHasCategories: 'category/assignmentHasCategories',
            assignmentCategories: 'category/assignmentCategories',
        }),
    },
}
</script>
