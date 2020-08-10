<template>
    <b-row
        class="outer-container-timeline-page"
        noGutters
    >
        <b-col
            md="12"
            lg="8"
            xl="9"
            class="inner-container-timeline-page"
        >
            <b-col
                md="12"
                lg="auto"
                xl="4"
                class="left-content-timeline-page"
            >
                <bread-crumb v-if="$root.lgMax"/>
                <timeline
                    v-if="!loadingNodes"
                    :selected="currentNode"
                    :nodes="nodes"
                    :assignment="assignment"
                    @select-node="selectNode"
                />
            </b-col>

            <b-col
                md="12"
                lg="auto"
                xl="8"
                class="main-content-timeline-page"
            >
                <bread-crumb v-if="$root.xl"/>
                <b-alert
                    v-if="!loadingNodes && journal.needs_lti_link.length > 0 && assignment.active_lti_course"
                    show
                >
                    <span v-if="assignment.is_group_assignment">
                        <b>Warning:</b> The following journal members have not visited the assignment in the active LMS
                        (Canvas) course '{{ assignment.active_lti_course.name }}' yet:
                        <ul>
                            <li
                                v-for="name in journal.needs_lti_link"
                                :key="`lti-author-${name}`"
                            >
                                {{ name }}
                            </li>
                        </ul>
                        This journal cannot be updated and grades cannot be passed back until each member visits the
                        assignment at least once.
                    </span>
                    <span v-else>
                        <b>Warning:</b> This student has not visited the assignment in the active LMS (Canvas) course
                        '{{ assignment.active_lti_course.name }}' yet. They cannot update this journal and grades cannot
                        be passed back until they visit the assignment at least once.
                    </span>
                </b-alert>
                <load-wrapper :loading="loadingNodes">
                    <div v-if="nodes.length > currentNode && currentNode !== -1">
                        <div v-if="nodes[currentNode].type == 'e' || nodes[currentNode].type == 'd'">
                            <entry-non-student-preview
                                ref="entry-template-card"
                                :journal="journal"
                                :entryNode="nodes[currentNode]"
                                :assignment="assignment"
                                @check-grade="loadJournal(true)"
                            />
                        </div>
                        <div v-else-if="nodes[currentNode].type == 'p'">
                            <progress-node
                                :currentNode="nodes[currentNode]"
                                :nodes="nodes"
                                :bonusPoints="journal.bonus_points"
                            />
                        </div>
                    </div>
                    <journal-start-card
                        v-else-if="currentNode === -1"
                        :assignment="assignment"
                    />
                    <journal-end-card
                        v-else
                        :assignment="assignment"
                    />
                </load-wrapper>
            </b-col>
        </b-col>

        <b-col
            md="12"
            lg="4"
            xl="3"
            class="right-content-timeline-page right-content"
        >
            <b-row>
                <b-col
                    md="6"
                    lg="12"
                    class="mb-2"
                >
                    <h3 class="theme-h3">
                        Details
                    </h3>
                    <b-card
                        :class="$root.getBorderClass($route.params.cID)"
                        class="journal-details-card no-hover"
                    >
                        <journal-details
                            v-if="!loadingNodes"
                            :journal="journal"
                            :assignment="assignment"
                        />
                    </b-card>
                    <div
                        v-if="filteredJournals.length > 1"
                        class="d-flex mb-2"
                    >
                        <b-button
                            v-if="filteredJournals.length !== 0"
                            :to="{ name: 'Journal', params: { cID: cID, aID: aID, jID: prevJournal.id } }"
                            class="mr-2 flex-grow-1"
                            tag="b-button"
                        >
                            <icon name="arrow-left"/>
                            Previous
                        </b-button>
                        <b-button
                            v-if="filteredJournals.length !== 0"
                            :to="{ name: 'Journal', params: { cID: cID, aID: aID, jID: nextJournal.id } }"
                            class="flex-grow-1"
                            tag="b-button"
                        >
                            Next
                            <icon name="arrow-right"/>
                        </b-button>
                    </div>
                </b-col>
                <b-col
                    v-if="journal && ($hasPermission('can_grade') || $hasPermission('can_publish_grades'))"
                    md="6"
                    lg="12"
                >
                    <h3 class="theme-h3">
                        Grading
                    </h3>
                    <div
                        v-if="$hasPermission('can_grade')"
                        class="bonus-section grade-section full-width"
                    >
                        <div>
                            <b-form-input
                                v-model="bonusPointsTemp"
                                type="number"
                                class="theme-input mr-2"
                                size="2"
                                placeholder="0"
                                min="0.0"
                            />
                            Bonus points
                        </div>
                        <b-button
                            class="add-button"
                            @click="commitBonus"
                        >
                            <icon
                                name="save"
                                scale="1"
                            />
                            Save bonus
                        </b-button>
                    </div>
                    <b-button
                        v-if="$hasPermission('can_publish_grades')"
                        class="add-button full-width"
                        @click="publishGradesJournal"
                    >
                        <icon name="upload"/>
                        Publish all grades
                    </b-button>
                </b-col>
            </b-row>
        </b-col>
    </b-row>
</template>

<script>
import entryNonStudentPreview from '@/components/entry/EntryNonStudentPreview.vue'
import timeline from '@/components/timeline/Timeline.vue'
import journalDetails from '@/components/journal/JournalDetails.vue'
import breadCrumb from '@/components/assets/BreadCrumb.vue'
import loadWrapper from '@/components/loading/LoadWrapper.vue'
import journalStartCard from '@/components/journal/JournalStartCard.vue'
import journalEndCard from '@/components/journal/JournalEndCard.vue'
import progressNode from '@/components/entry/ProgressNode.vue'

import store from '@/Store.vue'
import journalAPI from '@/api/journal.js'
import assignmentAPI from '@/api/assignment.js'
import { mapGetters, mapMutations } from 'vuex'

export default {
    components: {
        entryNonStudentPreview,
        breadCrumb,
        loadWrapper,
        timeline,
        journalDetails,
        journalStartCard,
        journalEndCard,
        progressNode,
    },
    props: ['cID', 'aID', 'jID'],
    data () {
        return {
            currentNode: -1,
            editedData: ['', ''],
            nodes: [],
            progressNodes: {},
            progressPointsLeft: 0,
            assignmentJournals: [],
            assignment: null,
            journal: null,
            loadingNodes: true,
            editingName: false,
            bonusPointsTemp: 0,
        }
    },
    computed: {
        ...mapGetters({
            getJournalSortBy: 'preferences/journalSortBy',
            order: 'preferences/journalSortAscending',
            getJournalSearchValue: 'preferences/journalSearchValue',
            getJournalGroupFilter: 'preferences/journalGroupFilter',
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
    methods: {
        ...mapMutations({
            switchJournalAssignment: 'preferences/SWITCH_JOURNAL_ASSIGNMENT',
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
                    this.currentNode = this.findEntryNode(parseInt(this.$route.query.nID, 10))
                } else {
                    this.selectFirstUngradedNode(gradeUpdated)
                }
            })
        },
        selectFirstUngradedNode (gradeUpdated) {
            let min = this.nodes.length

            for (let i = Math.max(this.currentNode, 0); i < this.nodes.length; i++) {
                if (this.nodes[i].entry && (this.nodes[i].entry.grade === null
                    || (this.nodes[i].entry.grade.grade === null || !this.nodes[i].entry.grade.published))) {
                    min = i
                    break
                }
            }

            if (min < this.nodes.length && this.$store.getters['preferences/autoSelectUngradedEntry']) {
                this.currentNode = min
            } else if (min === this.nodes.length && this.$store.getters['preferences/autoProceedNextJournal']
                && gradeUpdated && this.filteredJournals.length > 1) {
                this.$router.push({
                    name: 'Journal',
                    params: { cID: this.cID, aID: this.aID, jID: this.nextJournal.id },
                })
            }
        },
        adaptData (editedData) {
            this.nodes[this.currentNode] = editedData
        },
        selectNode ($event) {
            /* Function that prevents you from instant leaving an EntryNode
             * or a DeadlineNode when clicking on a different node in the
             * timeline. */
            if ($event === this.currentNode) {
                /* TODO fix mess */
            } else if (!this.discardChanges()) {
                /* pass */
            } else if (this.currentNode === -1 || this.currentNode >= this.nodes.length
                || this.nodes[this.currentNode].type !== 'e'
                || this.nodes[this.currentNode].type !== 'd') {
                this.currentNode = $event
            } else if (this.$refs['entry-template-card'].saveEditMode === 'Save') {
                window.confirm('Progress will not be saved if you leave. Do you wish to continue?')
            } else {
                this.currentNode = $event
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
        findEntryNode (nodeID) {
            for (let i = 0; i < this.nodes.length; i++) {
                if (this.nodes[i].nID === nodeID) {
                    return i
                }
            }
            return 0
        },
        findIndex (array, property, value) {
            for (let i = 0; i < array.length; i++) {
                if (String(array[i][property]) === String(value)) {
                    return i
                }
            }

            return false
        },
        discardChanges () {
            if (this.currentNode !== -1
                && this.currentNode < this.nodes.length
                && (this.nodes[this.currentNode].type === 'e'
                || (this.nodes[this.currentNode].type === 'd' && this.nodes[this.currentNode].entry !== null))) {
                if (this.nodes[this.currentNode].entry.grade === null) {
                    if (this.$refs['entry-template-card'].grade.grade > 0) {
                        if (!window.confirm('Progress will not be saved if you leave. Do you wish to continue?')) {
                            return false
                        }
                    }
                } else if (this.$refs['entry-template-card'].grade.grade
                           !== this.nodes[this.currentNode].entry.grade.grade
                           || this.$refs['entry-template-card'].grade.published
                           !== this.nodes[this.currentNode].entry.grade.published) {
                    if (!window.confirm('Progress will not be saved if you leave. Do you wish to continue?')) {
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
                    { customSuccessToast: 'Bonus succesfully added.' },
                )
                    .then((journal) => { this.journal = journal })
            }
        },
    },
}
</script>

<style lang="sass">
@import '~sass/modules/colors.sass'

.grade-section.bonus-section
    .btn
        display: block
        width: 100%
        border-width: 1px 0px 0px 0px !important
        border-radius: 0px 0px 5px 5px !important
    .theme-input, .theme-input:hover, .theme-input:focus
        margin-left: 0px
        font-size: 1.3em
        width: 3.5em
        display: inline-block
        padding-right: 0px !important

.journal-details-card > .card-body
    padding-top: 45px
</style>
