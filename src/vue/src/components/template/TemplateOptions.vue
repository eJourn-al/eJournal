<template>
    <b-table-simple>
        <b-thead>
            <b-tr>
                <b-th>
                    Options
                </b-th>
                <b-th class="template-availability">
                    <icon
                        name="info-circle"
                        class="shift-up-3 mr-1"
                    />
                    Information
                </b-th>
            </b-tr>
        </b-thead>

        <b-tbody>
            <b-tr>
                <b-td class="template-availability">
                    <b-button
                        :class="(template.preset_only) ? 'red-button' : 'green-button'"
                        @click.stop="template.preset_only = !template.preset_only"
                    >
                        <icon :name="(template.preset_only) ? 'lock' : 'unlock'"/>
                        {{ (template.preset_only) ? 'Preset-only' : 'Unlimited' }}
                    </b-button>
                </b-td>
                <b-td class="template-availability">
                    <icon
                        name="info-circle"
                        class="shift-up-3 mr-1"
                    />
                    <span v-if="template.preset_only">
                        This template can only be used for preset entries you add to the timeline
                    </span>
                    <span v-else>This template can be freely used by students as often as they want</span>
                </b-td>
            </b-tr>
            <b-tr>
                <b-td class="template-availability">
                    <b-button
                        :class="(template.fixed_categories) ? 'red-button' : 'green-button'"
                        @click.stop="template.fixed_categories = !template.fixed_categories"
                    >
                        <icon :name="(template.fixed_categories) ? 'lock' : 'unlock'"/>
                        {{ (template.fixed_categories) ? 'Fixed categories' : 'Custom categories' }}
                    </b-button>
                </b-td>
                <b-td class="template-availability">
                    <icon
                        name="info-circle"
                        class="shift-up-3 mr-1"
                    />
                    <span v-if="template.fixed_categories">
                        Students can not change the default categories for entries created with this template
                    </span>
                    <span v-else>
                        Students can freely add or remove categories to entries created with this template
                    </span>
                </b-td>
            </b-tr>
        </b-tbody>
    </b-table-simple>
</template>

<script>
export default {
    name: 'TemplateOptions',
    props: {
        template: {
            required: true,
            type: Object,
        },
    },
}
</script>

<style lang="sass">
.template-availability
    font-weight: bold
    color: grey
</style>
