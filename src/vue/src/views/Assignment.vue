<template>
    <!-- This check helps prevent user seeing the teacher view of the assignment user is not allowed to -->
    <content-columns v-if="$hasPermission('can_view_all_journals')">
        <bread-crumb slot="main-content-column"/>
        <b-alert
            v-if="LTILeftJournal"
            slot="main-content-column"
            show
            dismissible
        >
            <b>Warning:</b> The author of the submission you viewed in the LMS (Canvas) is no longer a member of any
            journal for this assignment.
        </b-alert>

        <div slot="main-content-column">
            <div
                v-if="assignmentJournals.length > 0"
                class="p-2 background-light-grey round-border mb-2"
            >
                <b-input
                    v-model="searchValue"
                    class="full-width"
                    type="text"
                    placeholder="Search..."
                />

                <div class="d-flex">
                    <theme-select
                        v-model="journalGroupFilter"
                        label="name"
                        trackBy="name"
                        :options="groups"
                        :multiple="true"
                        :searchable="true"
                        :multiSelectText="`active group filter${journalGroupFilter &&
                            journalGroupFilter.length === 1 ? '' : 's'}`"
                        placeholder="Filter By Group"
                        class="mt-2 mr-2"
                    />
                    <b-form-select
                        v-model="selectedSortOption"
                        :selectSize="1"
                        class="theme-select mt-2 mr-2"
                    >
                        <option value="name">
                            Sort by name
                        </option>
                        <option value="username">
                            Sort by username
                        </option>
                        <option value="markingNeeded">
                            Sort by marking needed
                        </option>
                        <option
                            v-if="$hasPermission('can_manage_journal_import_requests')
                                && !loadingJournals && assignment.stats.import_requests"
                            value="importRequests"
                        >
                            Sort by import requests
                        </option>
                        <option value="points">
                            Sort by points
                        </option>
                    </b-form-select>
                    <b-button
                        v-if="!order"
                        class="mt-2"
                        @click.stop
                        @click="toggleOrder(!order)"
                    >
                        <icon name="long-arrow-alt-down"/>
                        Ascending
                    </b-button>
                    <b-button
                        v-if="order"
                        class="mt-2"
                        @click.stop
                        @click="toggleOrder(!order)"
                    >
                        <icon name="long-arrow-alt-up"/>
                        Descending
                    </b-button>
                </div>
            </div>

            <bonus-file-upload-modal
                ref="bonusPointsModal"
                :aID="$route.params.aID"
                :endpoint="'assignments/' + $route.params.aID + '/add_bonus_points'"
                @bonusPointsSuccessfullyUpdated="hideModal('bonusPointsModal'); init()"
            />

            <assignment-spreadsheet-export-modal
                ref="assignmentExportSpreadsheetModal"
                :assignment="assignment"
                :filteredJournals="filteredJournals"
                :assignmentJournals="assignmentJournals"
                @spreadsheet-exported="hideModal('assignmentExportSpreadsheetModal')"
            />

            <post-teacher-entry-modal
                v-if="$hasPermission('can_post_teacher_entries')"
                ref="postTeacherEntry"
                :aID="aID"
                :assignmentJournals="assignmentJournals"
                @teacher-entry-posted="
                    hideModal('postTeacherEntry'); init();
                    if (assignment.has_teacher_entries) {$refs.manageTeacherEntries.loadTeacherEntries()}"
            />

            <manage-teacher-entries-modal
                v-if="$hasPermission('can_post_teacher_entries') && assignment.has_teacher_entries"
                ref="manageTeacherEntries"
                :aID="aID"
                :assignmentJournals="assignmentJournals"
                @teacher-entry-updated="hideModal('manageTeacherEntries'); init()"
            />

            <b-modal
                v-if="$hasPermission('can_edit_assignment') && assignment.lti_courses
                    && Object.keys(assignment.lti_courses).length > 1"
                ref="manageLTIModal"
                title="Select active LTI course"
                size="lg"
                noEnforceFocus
                @show="newActiveLTICourse = assignment.active_lti_course.cID"
                @hide="newActiveLTICourse = null"
            >
                This assignment is linked to multiple courses on your LMS.
                Grades can only be passed back to one course at a time.
                Select from the options below which course should be used for grade passback.<br/>
                <b-form-select
                    v-model="newActiveLTICourse"
                    class="theme-select full-width mt-2 mb-2"
                >
                    <option
                        v-for="(name, id) in assignment.lti_courses"
                        :key="`lti-option-${cID}-${id}`"
                        :value="parseInt(id)"
                    >
                        {{ name }}
                    </option>
                </b-form-select>

                <b class="text-red">Warning:</b> After changing this option, students will not be
                able to update their journals for this assignment until they visit the assignment
                on your LMS at least once.<br/>

                <template #modal-footer>
                    <b-button
                        class="green-button d-block float-right"
                        :class="{'input-disabled': assignment.active_lti_course.cID === newActiveLTICourse}"
                        @click="saveNewActiveLTICourse"
                    >
                        <icon name="save"/>
                        Save
                    </b-button>
                </template>
            </b-modal>
        </div>

        <load-wrapper
            slot="main-content-column"
            :loading="loadingJournals"
        >
            <div
                v-for="journal in filteredJournals"
                :key="journal.id"
            >
                <journal-card
                    :journal="journal"
                    :assignment="assignment"
                    @journal-deleted="journalDeleted(journal)"
                />
            </div>
            <not-found
                v-if="assignmentJournals.length === 0"
                subject="journals"
                :explanation="assignment.is_group_assignment ? 'Create journals by using the button below.' :
                    'No participants with a journal.'"
            >
                <b-button
                    v-if="$hasPermission('can_manage_journals') && assignment.is_group_assignment"
                    class="mt-2 green-button d-block"
                    @click="showModal('createJournalModal')"
                >
                    <icon name="plus"/>
                    Create new journals
                </b-button>
            </not-found>
            <not-found
                v-else-if="filteredJournals.length === 0"
                subject="journals"
                explanation="There are no journals that match your search query."
            />

            <b-modal
                v-if="$hasPermission('can_manage_journals') && assignment.is_group_assignment"
                ref="createJournalModal"
                title="Create new journals"
                size="lg"
                @show="resetNewJournals"
            >
                <b-form @submit.prevent="createNewJournals">
                    <h2 class="theme-h2 field-heading mb-2">
                        Name
                    </h2>
                    <b-input
                        v-model="newJournalName"
                        placeholder="Journal"
                        class="mb-2"
                    />
                    <h2 class="theme-h2 field-heading">
                        Member limit
                    </h2>
                    <b-input
                        v-model="newJournalMemberLimit"
                        type="number"
                        placeholder="No member limit"
                        min="2"
                        class="mb-2"
                    />
                </b-form>
                <template #modal-footer>
                    <div class="mr-auto">
                        <b-button
                            v-if="repeatCreateJournal"
                            class="mr-2"
                            @click="repeatCreateJournal = false"
                        >
                            <icon name="book"/>
                            Multiple journals
                        </b-button>
                        <b-button
                            v-else
                            class="mr-2"
                            @click="repeatCreateJournal = true"
                        >
                            <icon name="book"/>
                            Single journal
                        </b-button>
                        <template v-if="repeatCreateJournal">
                            Repeat
                            <b-form-input
                                v-model="newJournalCount"
                                type="number"
                                min="2"
                                class="inline"
                                required
                            />
                            times
                            <icon
                                v-b-tooltip:hover="'All journals created will be numbered sequentially'"
                                name="info-circle"
                            />
                        </template>
                    </div>

                    <b-button
                        class="green-button"
                        :class="{'input-disabled': newJournalRequestInFlight}"
                        @click="createNewJournals"
                    >
                        <icon name="plus-square"/>
                        Create
                    </b-button>
                </template>
            </b-modal>
        </load-wrapper>

        <b-row slot="right-content-column">
            <b-col
                v-if="stats"
                md="6"
                lg="12"
                class="mb-2"
            >
                <statistics-card :stats="stats"/>
            </b-col>
            <b-col
                v-if="canPerformActions && !loadingJournals"
                slot="right-content-column"
                md="6"
                lg="12"
            >
                <b-card>
                    <h3
                        slot="header"
                        class="theme-h3"
                    >
                        Actions
                    </h3>
                    <b-button
                        v-if="$hasPermission('can_edit_assignment')"
                        class="grey-button edit-button"
                        variant="link"
                        @click="openAssignmentEditor"
                    >
                        <icon name="cog"/>
                        Edit assignment
                    </b-button>
                    <b-button
                        v-if="canPublishGradesAssignment"
                        variant="link"
                        class="green-button"
                        @click="publishGradesAssignment"
                    >
                        <icon name="upload"/>
                        {{ assignment.journals.length === filteredJournals.length ?
                            "Publish all grades" : "Publish grades" }}
                    </b-button>
                    <b-button
                        v-if="canManageLTI"
                        variant="link"
                        class="green-button"
                        @click="showModal('manageLTIModal')"
                    >
                        <icon name="graduation-cap"/>
                        Manage LTI
                    </b-button>
                    <b-button
                        v-if="canImportBonusPoints"
                        variant="link"
                        class="orange-button"
                        @click="showModal('bonusPointsModal')"
                    >
                        <icon name="star"/>
                        Import bonus points
                    </b-button>
                    <b-button
                        v-if="canCreateJournals"
                        variant="link"
                        class=" green-button"
                        @click="showModal('createJournalModal')"
                    >
                        <icon name="plus"/>
                        Create new journals
                    </b-button>
                    <b-button
                        v-if="canExportResults"
                        variant="link"
                        class="green-button"
                        @click="showModal('assignmentExportSpreadsheetModal')"
                    >
                        <icon name="file-export"/>
                        Export results
                    </b-button>
                    <b-button
                        v-if="$hasPermission('can_post_teacher_entries')"
                        variant="link"
                        class="green-button"
                        @click="showModal('postTeacherEntry')"
                    >
                        <icon name="plus"/>
                        Post teacher entries
                    </b-button>
                    <b-button
                        v-if="$hasPermission('can_post_teacher_entries') && assignment.has_teacher_entries"
                        variant="link"
                        class="orange-button"
                        @click="showModal('manageTeacherEntries')"
                    >
                        <icon name="edit"/>
                        Manage teacher entries
                    </b-button>
                </b-card>
            </b-col>
        </b-row>
    </content-columns>
</template>

<script>
import BonusFileUploadModal from '@/components/assets/file_handling/BonusFileUploadModal.vue'
import BreadCrumb from '@/components/assets/BreadCrumb.vue'
import ContentColumns from '@/components/columns/ContentColumns.vue'
import JournalCard from '@/components/assignment/JournalCard.vue'
import LoadWrapper from '@/components/loading/LoadWrapper.vue'
import ManageTeacherEntriesModal from '@/components/assignment/ManageTeacherEntriesModal.vue'
import PostTeacherEntryModal from '@/components/assignment/PostTeacherEntryModal.vue'
import StatisticsCard from '@/components/assignment/StatisticsCard.vue'

import { mapGetters, mapMutations } from 'vuex'
import assignmentAPI from '@/api/assignment.js'
import gradeAPI from '@/api/grade.js'
import groupAPI from '@/api/group.js'
import journalAPI from '@/api/journal.js'
import participationAPI from '@/api/participation.js'
import store from '@/Store.vue'

const AssignmentSpreadsheetExportModal = () => import(
    /* webpackChunkName: 'assignment-spreadsheet-export-modal' */
    '@/components/assignment/AssignmentSpreadsheetExportModal.vue')

export default {
    name: 'Assignment',
    components: {
        AssignmentSpreadsheetExportModal,
        BonusFileUploadModal,
        BreadCrumb,
        ContentColumns,
        JournalCard,
        LoadWrapper,
        PostTeacherEntryModal,
        StatisticsCard,
        ManageTeacherEntriesModal,
    },
    props: {
        cID: {
            required: true,
        },
        aID: {
            required: true,
        },
    },
    data () {
        return {
            assignment: {},
            assignmentJournals: [],
            stats: null,
            groups: [],
            loadingJournals: true,
            newActiveLTICourse: null,
            filteredGroups: null,
            newJournalName: null,
            newJournalMemberLimit: null,
            repeatCreateJournal: false,
            newJournalCount: null,
            newJournalRequestInFlight: false,
            LTILeftJournal: false,
        }
    },
    computed: {
        ...mapGetters({
            journalSortBy: 'preferences/journalSortBy',
            isSuperuser: 'user/isSuperuser',
            order: 'preferences/journalSortAscending',
            getJournalSearchValue: 'preferences/journalSearchValue',
            getJournalGroupFilter: 'preferences/journalGroupFilter',
            getSelfSetGroupFilter: 'preferences/journalSelfSetGroupFilter',
        }),
        journalGroupFilter: {
            get () {
                return this.getJournalGroupFilter
            },
            set (value) {
                this.setJournalGroupFilter(value)
                this.setSelfSetGroupFilter(true)
            },
        },
        searchValue: {
            get () {
                return this.getJournalSearchValue
            },
            set (value) {
                this.setJournalSearchValue(value)
            },
        },
        selectedSortOption: {
            get () {
                return this.journalSortBy
            },
            set (value) {
                this.setJournalSortBy(value)
            },
        },
        filteredJournals () {
            store.setFilteredJournals(this.assignmentJournals, this.order, this.journalGroupFilter,
                this.getJournalSearchValue, this.journalSortBy)
            this.calcStats(store.state.filteredJournals)
            return store.state.filteredJournals
        },
        canPerformActions () {
            return this.canPublishGradesAssignment || this.canManageLTI || this.canImportBonusPoints
                || this.canExportResults || this.$hasPermission('can_post_teacher_entries')
                || this.canCreateJournals || this.$hasPermission('can_edit_assignment')
        },
        canPublishGradesAssignment  () {
            return this.$hasPermission('can_publish_grades') && this.assignmentJournals
                && this.assignmentJournals.length > 0
        },
        canManageLTI  () {
            return this.$hasPermission('can_edit_assignment') && this.assignment.lti_courses
                    && Object.keys(this.assignment.lti_courses).length > 1
        },
        canCreateJournals () {
            return this.$hasPermission('can_manage_journals') && this.assignment.is_group_assignment
        },
        canImportBonusPoints  () {
            return this.$hasPermission('can_publish_grades') && this.assignmentJournals
                && this.assignmentJournals.length > 0
        },
        canExportResults  () {
            return this.assignmentJournals && this.assignmentJournals.length > 0
        },
    },
    created () {
        // If a teacher manually links somewhere to an assignment
        // students will now be directly navigated to their journal
        if (!this.$hasPermission('can_view_all_journals', 'assignment', this.aID)) {
            assignmentAPI.get(this.aID, this.cID).then((assignment) => {
                this.$router.push(this.$root.assignmentRoute(assignment))
            })
            return
        }

        /* Check query to see if the LTI submission corresponds to a left journal. Remove query param to prevent
         * showing an alert on subsequent page visits / refreshes. */
        if (this.$route.query.left_journal) {
            const query = { ...this.$route.query }
            delete query.left_journal
            this.$router.replace({ query })
            this.LTILeftJournal = true
        }

        this.init()
    },
    methods: {
        ...mapMutations({
            setJournalSortBy: 'preferences/SET_JOURNAL_SORT_BY',
            toggleOrder: 'preferences/SET_JOURNAL_SORT_ASCENDING',
            setJournalSearchValue: 'preferences/SET_JOURNAL_SEARCH_VALUE',
            setJournalGroupFilter: 'preferences/SET_JOURNAL_GROUP_FILTER',
            switchJournalAssignment: 'preferences/SWITCH_JOURNAL_ASSIGNMENT',
            setSelfSetGroupFilter: 'preferences/SET_JOURNAL_SELF_SET_GROUP_FILTER',
        }),
        init () {
            this.switchJournalAssignment(this.aID)

            const initialCalls = []
            initialCalls.push(assignmentAPI.get(this.aID, this.cID))
            initialCalls.push(groupAPI.getFromAssignment(this.cID, this.aID))
            /* Superuser does not have any participation, this should not redict to error, nor give an error toast */
            if (!this.isSuperuser) {
                initialCalls.push(participationAPI.get(this.cID))
            }

            Promise.all(initialCalls).then((results) => {
                this.assignment = results[0]
                this.assignmentJournals = results[0].journals
                this.groups = results[1].sort((a, b) => b.name < a.name)
                if (!this.isSuperuser) {
                    const participant = results[2]
                    /* If the group filter has not been set, set it to the
                       groups of the user provided that yields journals. */
                    if (!this.getSelfSetGroupFilter && participant && participant.groups) {
                        this.setJournalGroupFilter(participant.groups.filter(
                            (participantGroup) => this.groups.some((group) => group.id === participantGroup.id)))
                    }
                }

                /* If there are no groups or the current group filter yields no journals, remove the filter. */
                if (!this.groups || this.filteredJournals.length === 0) {
                    this.setJournalGroupFilter(null)
                }
                this.loadingJournals = false
            })
        },
        showModal (ref) {
            this.$refs[ref].show()
        },
        hideModal (ref) {
            this.$refs[ref].hide()
        },
        openAssignmentEditor () {
            this.$router.push({
                name: 'AssignmentEditor',
                params: {
                    cID: this.cID,
                    aID: this.aID,
                },
            })
        },
        publishGradesAssignment () {
            if (this.assignment.journals.length === store.state.filteredJournals.length) {
                if (window.confirm('Are you sure you want to publish the grades for all journals?')) {
                    gradeAPI.publish_all_assignment_grades(this.aID, {
                        customErrorToast: 'Error while publishing all grades for this assignment.',
                        customSuccessToast: 'Published all grades for this assignment.',
                    }).then(() => {
                        assignmentAPI.get(this.aID, this.cID)
                            .then((assignment) => {
                                this.assignmentJournals = assignment.journals
                                this.stats = assignment.stats
                            })
                    })
                }
            } else if (window.confirm('Are you sure you want to publish the grades of the filtered journals?')) {
                const allJournals = []
                this.filteredJournals.forEach((journal) => {
                    allJournals.push(journalAPI.update(journal.id, { published: true }, {
                        customErrorToast: `Error while publishing grades for ${journal.name}.`,
                    }))
                })
                Promise.all(allJournals).then(() => {
                    this.$toasted.success('Published grades.')
                    assignmentAPI.get(this.aID, this.cID)
                        .then((assignment) => {
                            this.assignmentJournals = assignment.journals
                            this.stats = assignment.stats
                        })
                })
            }
        },
        saveNewActiveLTICourse () {
            if (window.confirm('Are you sure you want to change the active LTI course for grade passback?'
                + ' Students will not be able to update their journals for this assignment until they visit'
                + ' the assignment on your LMS at least once.')) {
                assignmentAPI.update(this.aID, {
                    update_lti_course: this.newActiveLTICourse,
                })
                    .then(() => {
                        this.$toasted.success('Updated active LTI course')
                        this.$refs.manageLTIModal.hide()
                    })
            }
        },
        calcStats (filteredJournals) {
            let needsMarking = 0
            let unpublished = 0
            let points = 0
            let importRequests = 0

            for (let i = 0; i < filteredJournals.length; i++) {
                needsMarking += filteredJournals[i].needs_marking
                unpublished += filteredJournals[i].unpublished
                points += filteredJournals[i].grade
                importRequests += ((filteredJournals[i].import_requests) ? filteredJournals[i].import_requests : 0)
            }
            this.stats = {
                needsMarking,
                unpublished,
                importRequests,
                averagePoints: points / filteredJournals.length,
            }
        },
        resetNewJournals () {
            this.newJournalName = null
            this.newJournalMemberLimit = null
            this.repeatCreateJournal = false
            this.newJournalCount = null
        },
        createNewJournals () {
            this.newJournalRequestInFlight = true
            if (!this.newJournalCount) {
                this.newJournalCount = 1
            }
            journalAPI.create({
                name: this.newJournalName,
                amount: this.newJournalCount,
                author_limit: this.newJournalMemberLimit > 1 ? this.newJournalMemberLimit : 0,
                assignment_id: this.assignment.id,
            })
                .then((journals) => {
                    this.assignment.journals = journals
                    this.assignmentJournals = journals
                    this.hideModal('createJournalModal')
                    this.newJournalRequestInFlight = false
                })
                .catch(() => { this.newJournalRequestInFlight = false })
        },
        journalDeleted (journal) {
            this.assignment.journals.splice(this.assignment.journals.indexOf(journal), 1)
            this.assignmentJournals = this.assignment.journals
        },
    },
}
</script>
