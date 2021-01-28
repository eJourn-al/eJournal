<!--
    Used in a card in the format editor to open template editor and delete templates from pool.
-->

<template>
    <div
        class="menu-item-link unselectable"
        :class="{ active: isActive }"
        @click="$emit('select-template', template)"
    >
        <icon
            v-b-tooltip:hover="(template.preset_only) ?
                'This template can only be used for preset entries you add to the timeline'
                : 'This template can be freely used by students as often as they want'
            "
            :name="(template.preset_only) ? 'lock' : 'unlock'"
            class="float-right ml-2"
            :class="(template.preset_only) ? 'fill-red' : 'fill-green'"
        />

        <icon
            name="trash"
            class="trash-icon ml-2 float-right"
            @click.native.stop="$emit('delete-template', template)"
        />

        <b class="max-one-line">
            {{ template.name }}
        </b>
    </div>
</template>

<script>
import { mapGetters } from 'vuex'

export default {
    name: 'TemplateMenuItem',
    props: {
        template: {
            required: true,
            type: Object,
        },
    },
    computed: {
        ...mapGetters({
            activeComponent: 'assignmentEditor/activeComponent',
            selectedTemplate: 'assignmentEditor/selectedTemplate',
            activeComponentOptions: 'assignmentEditor/activeComponentOptions',
        }),
        isActive () {
            return (
                this.activeComponent === this.activeComponentOptions.template
                && this.selectedTemplate.id === this.template.id
            )
        },
    },
}
</script>
