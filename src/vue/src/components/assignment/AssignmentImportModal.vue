<template>
    <b-modal
        :id="modalID"
        size="lg"
        title="Import assignment"
        noEnforceFocus
    >
        <p>
            This action will create a new assignment that is identical to the assignment of your choice.
            Existing journals are not imported and will remain accessible only from the original assignment.
        </p>

        <theme-select
            v-model="selectedCourse"
            label="name"
            trackBy="id"
            :options="courses"
            :multiple="false"
            :searchable="true"
            placeholder="Select A Course"
            class="mb-2"
            @select="() => {
                selectedAssignment = null
            }"
        />
        <theme-select
            v-if="selectedCourse"
            v-model="selectedAssignment"
            label="name"
            trackBy="id"
            :options="assignments"
            :multiple="false"
            :searchable="true"
            placeholder="Select An Assignment"
            class="mb-2"
        />

        <not-found
            v-if="!importableFormats"
            subject="assignments"
            explanation="Only assignments where you have permission to edit are available to import."
        />

        <template v-if="selectedAssignment !== null && shiftImportDates">
            Dates will be shifted by
            <b-form-input
                id="months"
                v-model="months"
                type="number"
                class="inline"
            />
            months
            <icon
                v-b-tooltip:hover="'The weekdays of the deadlines will be kept intact'"
                name="info-circle"
            />
        </template>
        <template #modal-footer>
            <b-button
                v-if="!shiftImportDates"
                class="mr-auto"
                :class="{ 'input-disabled': selectedAssignment === null }"
                @click="shiftImportDates = true"
            >
                <icon name="calendar"/>
                Shift Deadlines
            </b-button>
            <b-button
                v-else
                class="mr-auto"
                :class="{ 'input-disabled': selectedAssignment === null }"
                @click="shiftImportDates = false"
            >
                <icon name="calendar"/>
                Keep existing deadlines
            </b-button>
            <b-button
                class="orange-button"
                :class="{ 'input-disabled': selectedAssignment === null }"
                @click="importAssignment"
            >
                <icon name="file-import"/>
                Import
            </b-button>
        </template>
    </b-modal>
</template>

<script>
import assignmentAPI from '@/api/assignment.js'
import utils from '@/utils/generic_utils.js'

export default {
    props: {
        modalID: {
            required: true,
        },
        cID: {
            required: false,
            default: null,
        },
    },
    data () {
        return {
            selectedCourse: null,
            selectedAssignment: null,
            importableFormats: [],
            assignmentImportInFlight: false,
            shiftImportDates: true,
            months: 12,
        }
    },
    computed: {
        courses () {
            return this.importableFormats.map((importable) => {
                const course = { ...importable.course }
                course.name = utils.courseWithDatesDisplay(course)
                return course
            })
        },
        assignments () {
            return this.importableFormats.find((importable) => importable.course.id === this.selectedCourse.id)
                .assignments.map((assignment) => {
                    assignment.name = utils.assignmentWithDatesDisplay(assignment)
                    return assignment
                })
        },
    },
    created () {
        assignmentAPI.getImportable()
            .then((data) => {
                this.importableFormats = data
            })
    },
    methods: {
        importAssignment (e) {
            e.preventDefault()

            if (!this.assignmentImportInFlight && this.selectedAssignment) {
                this.assignmentImportInFlight = true
                assignmentAPI.import(this.selectedAssignment.id, {
                    course_id: this.cID,
                    months_offset: (!this.shiftImportDates || this.months === '') ? 0 : this.months,
                    launch_id: this.$route.query.launch_id,
                }, { customSuccessToast: 'Assignment successfully imported.' }).then((assignment) => {
                    this.assignmentImportInFlight = false

                    this.$store.commit('user/IMPORT_ASSIGNMENT_PERMISSIONS', {
                        sourceAssignmentID: this.selectedAssignment.id,
                        importAssignmentID: assignment.id,
                    })

                    if (!this.$route.query.launch_id) {
                        this.$router.push({
                            name: 'AssignmentEditor',
                            params: {
                                cID: this.cID,
                                aID: assignment.id,
                            },
                        })
                    } else {
                        this.$emit('assignmentImported', assignment)
                    }
                }).catch((error) => {
                    this.assignmentImportInFlight = false
                    throw error
                })
            }
        },
    },
}
</script>
