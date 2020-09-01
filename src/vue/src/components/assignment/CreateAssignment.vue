<template>
    <b-card class="no-hover">
        <assignment-details
            ref="assignmentDetails"
            :assignmentDetails="form"
        />
        <hr/>
        <b-button
            class="float-left change-button"
            type="reset"
            @click.prevent.stop="onReset"
        >
            <icon name="undo"/>
            Reset
        </b-button>
        <b-button
            class="float-right add-button"
            type="submit"
            @click.prevent.stop="onSubmit"
        >
            <icon name="plus-square"/>
            Create
        </b-button>
    </b-card>
</template>

<script>
import AssignmentDetails from '@/components/assignment/AssignmentDetails.vue'

import assignmentAPI from '@/api/assignment.js'

export default {
    name: 'CreateAssignment',
    components: {
        AssignmentDetails,
    },
    props: ['lti', 'page'],
    data () {
        return {
            form: {
                name: '',
                description: '',
                course_id: '',
                lti_id: null,
                points_possible: null,
                unlock_date: null,
                due_date: null,
                lock_date: null,
                is_published: null,
                is_group_assignment: false,
                can_set_journal_name: false,
                can_set_journal_image: false,
                can_lock_journal: false,
                remove_grade_upon_leaving_group: false,
            },
            reset: null,
        }
    },
    computed: {
        unlockDateConfig () {
            const additionalConfig = {}
            if (this.form.dueDate) {
                additionalConfig.maxDate = new Date(this.form.dueDate)
            } else if (this.form.lockDate) {
                additionalConfig.maxDate = new Date(this.form.lockDate)
            }
            return Object.assign({}, additionalConfig, this.$root.flatPickrTimeConfig)
        },
        dueDateConfig () {
            const additionalConfig = {}
            if (this.form.unlockDate) {
                additionalConfig.minDate = new Date(this.form.unlockDate)
            }
            if (this.form.lockDate) {
                additionalConfig.maxDate = new Date(this.form.lockDate)
            }
            return Object.assign({}, additionalConfig, this.$root.flatPickrTimeConfig)
        },
        lockDateConfig () {
            const additionalConfig = {}
            if (this.form.dueDate) {
                additionalConfig.minDate = new Date(this.form.dueDate)
            } else if (this.form.unlockDate) {
                additionalConfig.minDate = new Date(this.form.unlockDate)
            }
            return Object.assign({}, additionalConfig, this.$root.flatPickrTimeConfig)
        },
    },
    mounted () {
        if (this.lti !== undefined) {
            this.form.name = this.lti.ltiAssignName
            this.form.lti_id = this.lti.ltiAssignID
            this.form.points_possible = this.lti.ltiPointsPossible
            this.form.unlock_date = this.lti.ltiAssignUnlock.slice(0, -9)
            this.form.due_date = this.lti.ltiAssignDue.slice(0, -9)
            this.form.lock_date = this.lti.ltiAssignLock.slice(0, -9)
            this.form.course_id = this.$route.query.course_id || this.page.cID
            this.form.is_published = this.lti.ltiAssignPublished
        } else {
            this.form.course_id = this.$route.params.cID
        }
        this.reset = Object.assign({}, this.form)
    },
    methods: {
        onSubmit () {
            if (this.$refs.assignmentDetails && !this.$refs.assignmentDetails.validateDetails()) {
                return
            }
            assignmentAPI.create(this.form)
                .then((assignment) => {
                    this.$emit('handleAction', assignment.id)
                    this.onReset(undefined)
                    this.$store.dispatch('user/populateStore').catch(() => {
                        this.$toasted.error('The website might be out of sync, please login again.')
                    })
                })
        },
        onReset (evt) {
            if (evt !== undefined) {
                evt.preventDefault()
            }
            /* Reset form values */
            this.form.name = ''
            this.form.description = ''
            /* Due to defensive programming, resetting the rich text content does not work directly */
            this.$refs.assignmentDetails.$refs['text-editor-assignment-edit-description'].clearContent()
            this.form.course_id = ''
            this.form.points_possible = null
            this.form.unlock_date = null
            this.form.due_date = null
            this.form.lock_date = null
            this.form.is_group_assignment = false
            this.form.can_set_journal_name = false
            this.form.can_set_journal_image = false
            this.form.can_lock_journal = false
            this.form.remove_grade_upon_leaving_group = false

            /* Trick to reset/clear native browser form validation state */
            this.show = false
            this.$nextTick(() => { this.show = true })
        },
    },
}
</script>
