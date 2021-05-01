<template>
    <b-card
        v-if="$hasPermission('can_delete_assignment')"
        class="assignment-danger-zone border-red"
    >
        <h3
            slot="header"
            class="theme-h3 text-white"
        >
            Danger Zone
        </h3>
        <b-button
            :class="{
                'input-disabled': assignment.lti_courses && assignment.lti_courses.length > 1
                    && assignment.active_lti_course
                    && parseInt(assignment.active_lti_course.cID) ===
                        parseInt($route.params.cID)}"
            variant="link"
            class="red-button"
            @click="removeAssignment"
        >
            <icon name="trash"/>
            {{ assignment.courses.length > 1 ? 'Remove' : 'Delete' }} assignment
        </b-button>
    </b-card>
</template>

<script>
import { mapActions, mapGetters } from 'vuex'

export default {
    data () {
        return {
            removePrompt: `Are you sure you want to remove this assignment from the course?

Students will not be able to access their journal via this course anymore!

Type 'remove' to confirm.`,
            deletePrompt: `Are you sure you want to delete this assignment?

All corresponding journals will be irreversibly lost!

Type 'delete' to confirm.`,
        }
    },
    computed: {
        ...mapGetters({
            assignment: 'assignment/assignment',
        }),
    },
    methods: {
        ...mapActions({
            delete: 'assignment/delete',
        }),
        removeAssignment () {
            if (this.assignment.courses.length > 1) {
                const confirm = window.prompt(this.removePrompt)
                if (confirm === null || confirm.toLowerCase() !== 'remove') {
                    this.$toasted.error('Assignment not removed.')
                    return
                }
            } else {
                const confirm = window.prompt(this.deletePrompt)
                if (confirm === null || confirm.toLowerCase() !== 'delete') {
                    this.$toasted.error('Assignment not deleted.')
                    return
                }
            }

            this.delete({
                id: this.assignment.id,
                cID: this.$route.params.cID,
                connArgs: {
                    customSuccessToast: `Assignment ${this.assignment.courses.length > 1 ? 'removed' : 'deleted'}.`,
                },
            })
        },
    },
}
</script>

<style lang="sass">
.assignment-danger-zone
    .card-header
        background-color: $theme-red
</style>
