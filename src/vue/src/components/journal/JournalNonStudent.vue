<template>
    <timeline-layout>
        <template #left>
            <bread-crumb v-if="$root.lgMax"/>
            <timeline
                v-if="!loadingNodes"
                :nodes="nodes"
                :assignment="assignment"
            />
        </template>

        <template #center>
            <bread-crumb v-if="$root.xl"/>

            <user-missing-lti-link-warning
                v-if="!loadingNodes && journal.needs_lti_link.length > 0 && assignment.active_lti_course"
                :assignment="assignment"
                :journal="journal"
            />

            <load-wrapper :loading="loadingNodes">
                <journal-start-card
                    v-if="currentNode === startNode"
                    :assignment="assignment"
                />
                <journal-end-card
                    v-else-if="currentNode === endNode"
                    :assignment="assignment"
                />
                <entry-non-student
                    v-else-if="currentNode.type == 'e' || currentNode.type == 'd'"
                    ref="entry-template-card"
                    :journal="journal"
                    :entryNode="currentNode"
                    :assignment="assignment"
                    @check-grade="loadJournal(true)"
                />
                <progress-node
                    v-else-if="currentNode.type == 'p'"
                    :currentNode="currentNode"
                    :nodes="nodes"
                    :bonusPoints="journal.bonus_points"
                />
            </load-wrapper>
        </template>

        <template #right>
            <b-row>
                <b-col
                    md="6"
                    lg="12"
                    class="mb-2"
                >
                    <journal-details
                        v-if="!loadingNodes"
                        :journal="journal"
                        :assignment="assignment"
                    >
                        <div
                            v-if="filteredJournals.length > 1"
                            slot="footer"
                            class="d-flex"
                        >
                            <b-button
                                v-if="filteredJournals.length !== 0"
                                :to="{ name: 'Journal', params: { cID: cID, aID: aID, jID: prevJournal.id } }"
                                class="flex-grow-1 mr-1 flex-basis-50 grey-button"
                            >
                                <icon name="angle-left"/>
                                Previous
                            </b-button>
                            <b-button
                                v-if="filteredJournals.length !== 0"
                                :to="{ name: 'Journal', params: { cID: cID, aID: aID, jID: nextJournal.id } }"
                                class="flex-grow-1 flex-basis-50 grey-button"
                            >
                                Next
                                <icon name="angle-right"/>
                            </b-button>
                        </div>
                    </journal-details>
                </b-col>

                <b-col
                    v-if="journal && ($hasPermission('can_grade') || $hasPermission('can_publish_grades'))"
                    md="6"
                    lg="12"
                >
                    <b-card>
                        <h3
                            slot="header"
                            class="theme-h3"
                        >
                            Grading
                        </h3>
                        <b-button
                            v-if="$hasPermission('can_grade') && !showBonusInput"
                            variant="link"
                            class="yellow-button"
                            @click="showBonusInput = true"
                        >
                            <icon name="star"/>
                            Give bonus points
                        </b-button>
                        <b-input-group
                            v-if="showBonusInput"
                            class="mb-2 p-2 background-light-grey round-border"
                        >
                            <b-input-group-text
                                slot="prepend"
                                class="no-right-radius"
                            >
                                Bonus points
                            </b-input-group-text>
                            <b-form-input
                                v-model="bonusPointsTemp"
                                type="number"
                                class="no-left-radius"
                                size="2"
                                placeholder="0"
                                min="0.0"
                            />

                            <b-button
                                class="green-button full-width mt-1"
                                @click="commitBonus"
                            >
                                <icon name="save"/>
                                Save
                            </b-button>
                        </b-input-group>
                        <b-button
                            v-if="$hasPermission('can_publish_grades')"
                            variant="link"
                            class="green-button"
                            @click="publishGradesJournal"
                        >
                            <icon name="upload"/>
                            Publish all grades
                        </b-button>
                        <div v-if="$hasPermission('can_manage_journal_import_requests') && !loadingNodes">
                            <b-button
                                v-if="journal.import_requests"
                                v-b-modal="'journal-import-request-approval-modal'"
                                variant="link"
                                class="orange-button"
                            >
                                <icon name="file-import"/>
                                Manage Import Requests
                            </b-button>

                            <journal-import-request-approval-modal
                                v-if="journal.import_requests"
                                modalID="journal-import-request-approval-modal"
                                @jir-processed="loadJournal(false)"
                            />
                        </div>
                    </b-card>
                </b-col>
            </b-row>
        </template>
    </timeline-layout>
</template>

<script>
import BreadCrumb from '@/components/assets/BreadCrumb.vue'
import EntryNonStudent from '@/components/entry/EntryNonStudent.vue'
import JournalDetails from '@/components/journal/JournalDetails.vue'
import JournalEndCard from '@/components/journal/JournalEndCard.vue'
import JournalImportRequestApprovalModal from '@/components/journal/JournalImportRequestApprovalModal.vue'
import JournalStartCard from '@/components/journal/JournalStartCard.vue'
import LoadWrapper from '@/components/loading/LoadWrapper.vue'
import ProgressNode from '@/components/entry/ProgressNode.vue'
import Timeline from '@/components/timeline/Timeline.vue'
import TimelineLayout from '@/components/columns/TimelineLayout.vue'
import UserMissingLtiLinkWarning from '@/components/journal/UserMissingLtiLinkWarning.vue'

import { mapGetters, mapMutations } from 'vuex'
import assignmentAPI from '@/api/assignment.js'
import journalAPI from '@/api/journal.js'
import store from '@/Store.vue'

export default {
    components: {
        EntryNonStudent,
        BreadCrumb,
        LoadWrapper,
        Timeline,
        TimelineLayout,
        JournalDetails,
        JournalStartCard,
        JournalEndCard,
        JournalImportRequestApprovalModal,
        ProgressNode,
        UserMissingLtiLinkWarning,
    },
    props: ['cID', 'aID', 'jID'],
    data () {
        return {
            editedData: ['', ''],
            nodes: [],
            assignmentJournals: [],
            assignment: null,
            journal: null,
            loadingNodes: true,
            bonusPointsTemp: 0,
            showBonusInput: false,
        }
    },
    computed: {
        ...mapGetters({
            getJournalSortBy: 'preferences/journalSortBy',
            order: 'preferences/journalSortAscending',
            getJournalSearchValue: 'preferences/journalSearchValue',
            getJournalGroupFilter: 'preferences/journalGroupFilter',
            currentNode: 'timeline/currentNode',
            startNode: 'timeline/startNode',
            addNode: 'timeline/addNode',
            endNode: 'timeline/endNode',
            preferences: 'preferences/saved',
        }),
        filteredJournals () {
            if (this.assignmentJournals.length > 0) {
                store.setFilteredJournals(this.assignmentJournals, this.order, this.getJournalGroupFilter,
                    this.getJournalSearchValue, this.getJournalSortBy)
            }
            return store.state.filteredJournals
        },
        prevJournal () {
            const curIndex = this.findIndex(this.filteredJournals, 'id', this.jID)
            const prevIndex = (curIndex - 1 + this.filteredJournals.length) % this.filteredJournals.length

            return this.filteredJournals[prevIndex]
        },
        nextJournal () {
            const curIndex = this.findIndex(this.filteredJournals, 'id', this.jID)
            const nextIndex = (curIndex + 1) % this.filteredJournals.length

            return this.filteredJournals[nextIndex]
        },
    },
    created () {
        this.setCurrentNode(this.startNode)
        this.pushNodeNavigationGuard(this.safeToLeave)
        this.switchJournalAssignment(this.aID)

        assignmentAPI.get(this.aID)
            .then((assignment) => {
                this.assignment = assignment
                this.loadJournal(false)
            })

        if (store.state.filteredJournals.length === 0) {
            if (this.$hasPermission('can_view_all_journals')) {
                journalAPI.getFromAssignment(this.cID, this.aID)
                    .then((journals) => { this.assignmentJournals = journals })
            }
        }
    },
    beforeDestroy () {
        this.removeNodeNavigationGuard(this.safeToLeave)
    },
    methods: {
        ...mapMutations({
            switchJournalAssignment: 'preferences/SWITCH_JOURNAL_ASSIGNMENT',
            setCurrentNode: 'timeline/SET_CURRENT_NODE',
            pushNodeNavigationGuard: 'timeline/PUSH_NODE_NAVIGATION_GUARD',
            removeNodeNavigationGuard: 'timeline/REMOVE_NODE_NAVIGATION_GUARD',
        }),
        loadJournal (gradeUpdated) {
            const initialCalls = []

            initialCalls.push(journalAPI.get(this.jID))
            initialCalls.push(journalAPI.getNodes(this.jID))

            Promise.all(initialCalls).then((results) => {
                this.journal = results[0]
                this.bonusPointsTemp = this.journal.bonus_points
                this.nodes = results[1]
                this.loadingNodes = false
                if (this.$route.query.nID !== undefined) {
                    const nID = parseInt(this.$route.query.nID, 10)
                    const nodeToSelect = this.nodes.find((node) => node.id === nID)
                    this.setCurrentNode(nodeToSelect || this.startNode)
                } else {
                    this.selectFirstUngradedNode(gradeUpdated)
                }
            })
        },
        selectFirstUngradedNode (gradeUpdated) {
            const currentNodeIndex = Math.max(
                this.nodes.findIndex((node) => (
                    node === this.currentNode || (this.currentNode.id && node.id === this.currentNode.id)
                )),
                0,
            )
            const firstUngradedNode = this.nodes.find((node, i) => (
                i > currentNodeIndex
                && node.entry
                && (node.entry.grade === null || (node.entry.grade.grade === null || !node.entry.grade.published))
            ))

            if (firstUngradedNode && this.preferences.auto_select_ungraded_entry) {
                this.setCurrentNode(firstUngradedNode)
            } else if (
                !firstUngradedNode
                && gradeUpdated
                && this.preferences.auto_proceed_next_journal
                && this.filteredJournals.length > 1
            ) {
                this.$router.push({
                    name: 'Journal',
                    params: { cID: this.cID, aID: this.aID, jID: this.nextJournal.id },
                })
            }
        },
        publishGradesJournal () {
            if (window.confirm('Are you sure you want to publish all grades for this journal?')) {
                journalAPI.update(this.jID, { published: true }, {
                    customSuccessToast: 'Published all grades for this journal.',
                    customErrorToast: 'Error while publishing all grades for this journal.',
                })
                    .then(() => {
                        journalAPI.getNodes(this.jID)
                            .then((nodes) => {
                                this.nodes = nodes
                                this.loadingNodes = false
                            })
                        journalAPI.get(this.jID)
                            .then((journal) => { this.journal = journal })
                    })
            }
        },
        findIndex (array, property, value) {
            for (let i = 0; i < array.length; i++) {
                if (String(array[i][property]) === String(value)) {
                    return i
                }
            }

            return false
        },
        /* Checks if a pending grade exists */
        safeToLeave () {
            const nonStudentEntryRef = this.$refs['entry-template-card']

            if (this.currentNode && this.currentNode.entry && nonStudentEntryRef) {
                const pendingGrade = nonStudentEntryRef.grade
                const actualGrade = this.currentNode.entry.grade
                const defaultGrade = this.currentNode.entry.template.default_grade

                if (!actualGrade) {
                    if (pendingGrade.grade > 0
                        && parseFloat(pendingGrade.grade) !== defaultGrade
                        && !window.confirm('Grade will not be saved if you leave. Do you wish to continue?')) {
                        return false
                    }
                } else if (parseFloat(pendingGrade.grade) !== actualGrade.grade
                           || pendingGrade.published !== actualGrade.published) {
                    if (!window.confirm('Grade will not be saved if you leave. Do you wish to continue?')) {
                        return false
                    }
                }
            }

            return true
        },
        commitBonus () {
            if (this.bonusPointsTemp !== null && this.bonusPointsTemp !== '') {
                journalAPI.update(
                    this.journal.id,
                    { bonus_points: this.bonusPointsTemp },
                    { customSuccessToast: 'Successfully updated bonus points.' },
                )
                    .then((journal) => {
                        this.journal = journal
                        this.showBonusInput = false
                    })
            }
        },
    },
}
</script>
