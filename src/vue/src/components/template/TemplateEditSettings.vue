<template>
    <b-card class="no-hover">
        <radio-button
            v-model="template.preset_only"
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
            Unlimited use
        </h2>
        Allow students to use this template for new entries in their journal.
        When disabled, this template can still be used for deadlines you add to the timeline.

        <hr/>

        <b-form-input
            id="default-grade-input"
            v-model="template.default_grade"
            type="number"
            class="theme-input float-right mb-3 ml-3"
            size="2"
            placeholder="-"
            min="0.0"
            :formatter="defaultGradeFormatter"
        />
        <h2 class="theme-h2 field-heading multi-form">
            Default grade
        </h2>
        Value which is used to prepopulate the grade field of entries making using of this template. The grade still
        needs to be approved by an educator, but this setting can be used to speedup the grading process.

        <template v-if="assignmentHasCategories">
            <hr/>
            <radio-button
                v-model="template.allow_custom_categories"
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
    methods: {
        defaultGradeFormatter (value) {
            if (value === '') { return null }
            return parseFloat(value)
        },
    },
}
</script>

<style lang="sass">
#default-grade-input
    width: 4em
</style>
