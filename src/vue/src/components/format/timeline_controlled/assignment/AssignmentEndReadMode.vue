<template>
    <journal-end-card :assignment="assignment">
        <template v-slot:edit-button>
            <b-button
                class="ml-2 orange-button float-right"
                @click.stop="setModeToEdit()"
            >
                <icon name="edit"/>
                Edit
            </b-button>
        </template>
    </journal-end-card>
</template>

<script>
import JournalEndCard from '@/components/journal/JournalEndCard.vue'

import { mapGetters, mapMutations } from 'vuex'

export default {
    components: {
        JournalEndCard,
    },
    computed: {
        ...mapGetters({
            assignment: 'assignment/assignment',
        }),
    },
    methods: {
        ...mapMutations({
            setModeToEdit: 'assignmentEditor/SET_ACTIVE_COMPONENT_MODE_TO_EDIT',
        }),
    },
}
</script>

<style>

</style>
