<template>
    <content-columns>
        <bread-crumb
            slot="main-content-column"
            @edit-click="handleEdit()"
        />

        <load-wrapper
            slot="main-content-column"
            :loading="loadingAssignments"
        >
            <div
                v-for="a in assignments"
                :key="a.id"
            >
                <b-link
                    :to="$root.assignmentRoute(a)"
                    tag="b-button"
                >
                    <assignment-card
                        :assignment="a"
                        :uniqueName="!assignments.some(a2 =>
                            a.name === a2.name && a.id !== a2.id
                        )"
                    >
                        <b-button
                            v-if="$hasPermission('can_edit_assignment', 'assignment', a.id)"
                            class="change-button float-right"
                            @click.prevent.stop="editAssignment(a)"
                        >
                            <icon name="edit"/>
                            Edit
                        </b-button>
                    </assignment-card>
                </b-link>
            </div>
            <main-card
                v-if="assignments !== null && assignments.length === 0"
                line1="No assignments found"
                line2="This course currently does not have any assignments."
                class="no-hover border-dark-grey"
            />
            <b-button
                v-if="$hasPermission('can_add_assignment', 'course', cID)"
                class="add-button mr-2 mb-2"
                @click="showModal('createAssignmentRef')"
            >
                <icon name="plus"/>
                Create new assignment
            </b-button>
            <b-button
                v-if="$hasPermission('can_add_assignment', 'course', cID)"
                v-b-modal="'course-assignment-import-modal'"
                class="change-button mb-2"
            >
                <icon name="file-import"/>
                Import Assignment
            </b-button>
            <assignment-import-modal
                modalID="course-assignment-import-modal"
                :cID="cID"
            />
        </load-wrapper>

        <b-modal
            slot="main-content-column"
            ref="createAssignmentRef"
            title="Create new assignment"
            size="lg"
            hideFooter
            noEnforceFocus
        >
            <create-assignment @handleAction="handleCreated"/>
        </b-modal>

        <deadline-deck slot="right-content-column"/>
    </content-columns>
</template>

<script>
import contentColumns from '@/components/columns/ContentColumns.vue'
import breadCrumb from '@/components/assets/BreadCrumb.vue'
import loadWrapper from '@/components/loading/LoadWrapper.vue'
import assignmentCard from '@/components/assignment/AssignmentCard.vue'
import mainCard from '@/components/assets/MainCard.vue'
import createAssignment from '@/components/assignment/CreateAssignment.vue'
import deadlineDeck from '@/components/assets/DeadlineDeck.vue'
import assignmentImportModal from '@/components/assignment/AssignmentImportModal.vue'

import assignmentAPI from '@/api/assignment.js'

export default {
    name: 'Course',
    components: {
        contentColumns,
        breadCrumb,
        loadWrapper,
        assignmentCard,
        mainCard,
        createAssignment,
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
            assignments: null,
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
        handleEdit () {
            this.$router.push({
                name: 'CourseEdit',
                params: {
                    cID: this.cID,
                },
            })
        },
        editAssignment (assignment) {
            this.$router.push({
                name: 'FormatEdit',
                params: {
                    cID: this.cID,
                    aID: assignment.id,
                },
            })
        },
        handleCreated (aID) {
            this.$router.push({
                name: 'FormatEdit',
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
