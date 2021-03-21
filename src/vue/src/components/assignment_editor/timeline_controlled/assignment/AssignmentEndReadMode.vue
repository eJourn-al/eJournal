<template>
    <journal-end-card :assignment="assignment">
        <template #edit-button>
            <b-button
                class="ml-auto orange-button"
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
