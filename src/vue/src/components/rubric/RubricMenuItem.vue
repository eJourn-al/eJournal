<template>
    <div
        class="menu-item-link unselectable"
        :class="{ active: isActive }"
        @click="$emit('select-rubric', rubric)"
    >
        <icon
            name="trash"
            class="trash-icon ml-2 float-right"
            @click.native.stop="$emit('delete-rubric', rubric)"
        />

        <span
            class="max-one-line"
            :class="{ dirty: isRubricDirty(rubric) }"
        >
            {{ rubric.name }}
        </span>
    </div>
</template>

<script>
import { mapGetters } from 'vuex'

export default {
    props: {
        rubric: {
            required: true,
            type: Object,
        },
    },
    computed: {
        ...mapGetters({
            activeComponent: 'assignmentEditor/activeComponent',
            selectedRubric: 'assignmentEditor/selectedRubric',
            activeComponentOptions: 'assignmentEditor/activeComponentOptions',
            isRubricDirty: 'assignmentEditor/isRubricDirty',
        }),
        isActive () {
            return (
                this.activeComponent === this.activeComponentOptions.rubric
                && this.selectedRubric.id === this.rubric.id
            )
        },
    },
}
</script>
