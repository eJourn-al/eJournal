<template>
    <content-columns>
        <bread-crumb slot="main-content-column"/>

        <load-wrapper
            slot="main-content-column"
            :loading="loadingAssignments"
        >
            <b-table-simple
                v-if="assignments.length > 0"
                responsive
                striped
                hover
                class="mt-2 mb-0 bordered-content no-top-table-border"
            >
                <b-thead>
                    <b-tr>
                        <b-th>
                            Name
                        </b-th>
                        <b-th>
                            Details
                        </b-th>
                        <b-th
                            v-if="assignments.some(
                                assignment => $hasPermission('can_edit_assignment', 'assignment', assignment.id)
                            )"
                        />
                    </b-tr>
                </b-thead>
                <b-tbody>
                    <b-tr
                        v-for="(assignment, i) in assignments"
                        :key="i"
                        class="cursor-pointer"
                        @click="$router.push($root.assignmentRoute(assignment))"
                    >
                        <b-td :title="assignment.name">
                            <b-link
                                :to="$root.assignmentRoute(assignment)"
                                @click.prevent.stop
                            >
                                <span class="mr-2">
                                    {{ assignment.name }}
                                </span>
                            </b-link>
                        </b-td>
                        <b-td>
                            <b-badge
                                v-if="assignment.lti_couples > 0"
                                v-b-tooltip:hover="'Linked via LTI'"
                                pill
                                class="align-middle mr-2 background-green"
                            >
                                LTI
                            </b-badge>
                            <b-badge
                                v-if="!assignment.is_published"
                                v-b-tooltip:hover="'Not visible to students: click to edit'"
                                pill
                                class="align-middle mr-2"
                            >
                                Unpublished
                            </b-badge>
                            <assignment-date-display-badge :assignment="assignment"/>
                        </b-td>
                        <b-td v-if="$hasPermission('can_edit_assignment', 'assignment', assignment.id)">
                            <b-button
                                class="grey-button float-right"
                                variant="link"
                                @click.prevent.stop="editAssignment(assignment)"
                            >
                                <icon name="cog"/>
                                Edit
                            </b-button>
                        </b-td>
                    </b-tr>
                </b-tbody>
            </b-table-simple>
            <not-found
                v-else
                subject="assignments"
                explanation="This course currently does not have any assignments."
            >
                <b-button
                    v-if="$hasPermission('can_add_assignment')"
                    class="green-button d-block ml-auto mr-auto mt-2"
                    @click="showModal('createAssignmentRef')"
                >
                    <icon name="plus"/>
                    Create new assignment
                </b-button>
            </not-found>
            <assignment-import-modal
                modalID="course-assignment-import-modal"
                :cID="cID"
            />
        </load-wrapper>

        <create-assignment-modal
            slot="main-content-column"
            ref="createAssignmentRef"
            @handleAction="handleCreated"
        />

        <template slot="right-content-column">
            <deadline-deck class="mb-3"/>
            <b-card
                v-if="$hasPermission('can_edit_course_details') || $hasPermission('can_add_assignment')"
            >
                <h3
                    slot="header"
                    class="theme-h3"
                >
                    Actions
                </h3>
                <b-button
                    v-if="$hasPermission('can_edit_course_details')"
                    variant="link"
                    class="grey-button"
                    @click="openCourseSettings"
                >
                    <icon name="cog"/>
                    Manage course
                </b-button>
                <b-button
                    v-if="$hasPermission('can_add_assignment')"
                    variant="link"
                    class="green-button"
                    @click="showModal('createAssignmentRef')"
                >
                    <icon name="plus"/>
                    Create new assignment
                </b-button>
                <b-button
                    v-if="$hasPermission('can_add_assignment')"
                    v-b-modal="'course-assignment-import-modal'"
                    variant="link"
                    class="orange-button"
                >
                    <icon name="file-import"/>
                    Import Assignment
                </b-button>
            </b-card>
        </template>
    </content-columns>
</template>

<script>
import AssignmentDateDisplayBadge from '@/components/assignment/AssignmentDateDisplayBadge.vue'
import assignmentImportModal from '@/components/assignment/AssignmentImportModal.vue'
import breadCrumb from '@/components/assets/BreadCrumb.vue'
import contentColumns from '@/components/columns/ContentColumns.vue'
import createAssignmentModal from '@/components/assignment/CreateAssignmentModal.vue'
import deadlineDeck from '@/components/assets/DeadlineDeck.vue'
import loadWrapper from '@/components/loading/LoadWrapper.vue'

import assignmentAPI from '@/api/assignment.js'

export default {
    name: 'Course',
    components: {
        AssignmentDateDisplayBadge,
        contentColumns,
        breadCrumb,
        loadWrapper,
        createAssignmentModal,
        deadlineDeck,
        assignmentImportModal,
    },
    props: {
        cID: {
            required: true,
        },
    },
    data () {
        return {
            assignments: [],
            cardColor: '',
            post: null,
            error: null,
            loadingAssignments: true,
        }
    },
    created () {
        this.loadAssignments()
    },
    methods: {
        loadAssignments () {
            assignmentAPI.list(this.cID)
                .then((assignments) => {
                    this.assignments = assignments
                    this.loadingAssignments = false
                })
        },
        openCourseSettings () {
            this.$router.push({
                name: 'CourseEdit',
                params: {
                    cID: this.cID,
                },
            })
        },
        editAssignment (assignment) {
            this.$router.push({
                name: 'AssignmentEditor',
                params: {
                    cID: this.cID,
                    aID: assignment.id,
                },
            })
        },
        handleCreated (aID) {
            this.$router.push({
                name: 'AssignmentEditor',
                params: {
                    cID: this.cID,
                    aID,
                },
            })
        },
        showModal (ref) {
            this.$refs[ref].show()
        },
    },
}
</script>
