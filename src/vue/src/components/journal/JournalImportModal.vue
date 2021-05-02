<template>
    <b-modal
        id="journalImportModal"
        ref="journalImportModal"
        size="lg"
        title="Import journal"
        noEnforceFocus
    >
        <p>
            Please select a journal to import. Your request will be sent to your educator for approval. Once
            approved, the entries of the selected journal will be added to your journal. The transfer of existing
            grades remains at the discretion of your eduator.
        </p>

        <load-wrapper
            :loading="loading"
        >
            <div v-if="courses && courses.length > 0">
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
            </div>

            <not-found
                v-else
                subject="journals"
                explanation="You can only import your own journals from other assignments."
            />
        </load-wrapper>
        <template #modal-footer>
            <b-button
                class="orange-button float-right"
                :class="{ 'input-disabled': !selectedAssignment }"
                @click="importJournal(selectedAssignment)"
            >
                <icon name="file-import"/>
                Import journal
            </b-button>
        </template>
    </b-modal>
</template>

<script>
import assignmentAPI from '@/api/assignment.js'
import courseAPI from '@/api/course.js'
import jirAPI from '@/api/journal_import_request.js'
import loadWrapper from '@/components/loading/LoadWrapper.vue'
import utils from '@/utils/generic_utils.js'

export default {
    components: {
        loadWrapper,
    },
    props: {
        targetAssignmentID: {
            required: true,
            type: Number,
        },
    },
    data () {
        return {
            fetchedCourses: [],
            fetchedAssignments: [],
            selectedAssignment: null,
            selectedCourse: null,
            loading: true,
            previewJournal: false,
        }
    },
    computed: {
        courses () {
            const courses = this.fetchedCourses.filter((c) => this.fetchedAssignments.some((a) => a.course.id === c.id))
            courses.map((c) => {
                c.name = utils.courseWithDatesDisplay(c)
                return c
            })
            return courses
        },
        assignments () {
            return this.fetchedAssignments
                .filter((a) => a.course.id === this.selectedCourse.id)
                .map((a) => {
                    a.name = utils.assignmentWithDatesDisplay(a)
                    return a
                })
        },
    },
    created () {
        const initCalls = []

        courseAPI.list()
            .then((courses) => {
                this.fetchedCourses = courses
                courses.forEach((c) => {
                    initCalls.push(assignmentAPI.list(c.id))
                })

                Promise.all(initCalls).then((results) => {
                    results.forEach((assignments) => {
                        this.fetchedAssignments = [
                            ...this.fetchedAssignments,
                            ...assignments.filter((a) => a.id !== this.targetAssignmentID),
                        ]
                    })

                    this.loading = false
                })
            })
    },
    methods: {
        importJournal (assignment) {
            if (window.confirm(
                `Are you sure you want to request to import your journal from the assignment: ${assignment.name}?`)) {
                jirAPI.create(
                    { assignment_source_id: assignment.id, assignment_target_id: this.targetAssignmentID },
                    { responseSuccessToast: true },
                ).then(() => {
                    this.selectedCourse = null
                    this.selectedAssignment = null
                    this.fetchedAssignments = this.fetchedAssignments.filter((a) => a.id !== assignment.id)
                    this.$refs.journalImportModal.hide()
                })
            }
        },
    },
}
</script>
