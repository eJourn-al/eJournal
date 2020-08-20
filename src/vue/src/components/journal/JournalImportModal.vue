<template>
    <b-modal
        :id="modalID"
        :ref="modalID"
        size="lg"
        title="Import journal"
        hideFooter
        noEnforceFocus
    >
        <b-card class="no-hover">
            <h2 class="theme-h2 multi-form">
                Select a journal to import
            </h2>

            <p>
                Please select a journal to import. Your request will be sent to your educator for approval. Once
                approved, the entries of the selected journal will be added to your journal. The reuse of existing
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
                        class="multi-form"
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
                        class="multi-form"
                    />

                    <b-button
                        class="change-button float-right"
                        :class="{ 'input-disabled': !selectedAssignment }"
                        @click="importJournal(selectedAssignment)"
                    >
                        <icon name="file-import"/>
                        Import journal
                    </b-button>
                </div>

                <div v-else>
                    <h4 class="theme-h4">
                        No importable journals available.
                    </h4>
                    <hr class="m-0 mb-1"/>
                    You can only import journal you own journals, and you cannot import the same journal into itself.
                </div>
            </load-wrapper>
        </b-card>
    </b-modal>
</template>

<script>
import loadWrapper from '@/components/loading/LoadWrapper.vue'

import assignmentAPI from '@/api/assignment.js'
import courseAPI from '@/api/course.js'
import jirAPI from '@/api/journal_import_request.js'

export default {
    components: {
        loadWrapper,
    },
    props: {
        modalID: {
            required: true,
            type: String,
        },
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
            return this.fetchedCourses.filter(c => this.fetchedAssignments.some(a => a.course.id === c.id))
        },
        assignments () {
            return this.fetchedAssignments.filter(a => a.course.id === this.selectedCourse.id)
        },
    },
    created () {
        const initCalls = []

        courseAPI.getUserEnrolled()
            .then((courses) => {
                this.fetchedCourses = courses
                courses.forEach((c) => {
                    initCalls.push(assignmentAPI.list(c.id))
                })

                Promise.all(initCalls).then((results) => {
                    results.forEach((assignments) => {
                        this.fetchedAssignments = [
                            ...this.fetchedAssignments,
                            ...assignments.filter(a => a.id !== this.targetAssignmentID),
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
                    this.fetchedAssignments = this.fetchedAssignments.filter(a => a.id !== assignment.id)
                })
            }
        },
    },
}
</script>
