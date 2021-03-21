<template>
    <journal-start-card :assignment="assignment">
        <template v-slot:edit-button>
            <b-button
                class="ml-auto orange-button"
                @click.stop="setModeToEdit()"
            >
                <icon name="edit"/>
                Edit
            </b-button>
        </template>
    </journal-start-card>
</template>

<script>
import JournalStartCard from '@/components/journal/JournalStartCard.vue'

import { mapGetters, mapMutations } from 'vuex'

export default {
    components: {
        JournalStartCard,
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
