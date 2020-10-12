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
                <bread-crumb v-if="$root.lgMax">
                    <template v-if="!loadingNodes && assignment.is_group_assignment">
                        - {{ journal.name }}
                    </template>
                </bread-crumb>
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
                <bread-crumb v-if="$root.xl">
                    <template v-if="!loadingNodes && assignment.is_group_assignment">
                        - {{ journal.name }}
                    </template>
                </bread-crumb>
                <b-alert
                    v-if="!loadingNodes && journal.needs_lti_link.length > 0 && assignment.active_lti_course"
                    show
                >
                    <b>Warning:</b> You cannot update this journal until
                    {{ assignment.is_group_assignment ? 'all group members' : 'you' }}
                    visit the assignment though the LMS (Canvas) course
                    '{{ assignment.active_lti_course.name }}' at least once.
                </b-alert>
                <load-wrapper :loading="loadingNodes">
                    <template
                        v-if="nodes[currentNode] && nodes[currentNode].type == 'a'"
                    >
                        <h4 class="theme-h4 mb-2 d-block">
                            <span>
                                New entry
                            </span>
                        </h4>
                        <b-form-select
                            v-if="nodes[currentNode].templates.length > 1"
                            v-model="selectedTemplate"
                            class="theme-select mb-2"
                        >
                            <option
                                :value="null"
                                disabled
                            >
                                Select a template
                            </option>
                            <option
                                v-for="template in nodes[currentNode].templates"
                                :key="template.id"
                                :value="template"
                            >
                                {{ template.name }}
                            </option>
                        </b-form-select>
                    </template>
                    <journal-start-card
                        v-if="currentNode === -1"
                        :assignment="assignment"
                    />
                    <journal-end-card
                        v-else-if="currentNode >= nodes.length"
                        :assignment="assignment"
                    />
                    <progress-node
                        v-else-if="nodes[currentNode].type == 'p'"
                        :currentNode="nodes[currentNode]"
                        :nodes="nodes"
                        :bonusPoints="journal.bonus_points"
                    />
                    <b-card
                        v-else-if="nodes[currentNode].type == 'd' && !nodes[currentNode].entry && currentNodeIsLocked"
                        :class="$root.getBorderClass($route.params.cID)"
                        class="no-hover"
                    >
                        <h2 class="theme-h2 mb-2">
                            {{ nodes[currentNode].template.name }}
                        </h2>
                        <hr class="full-width"/>
                        <b>This preset is locked. You cannot submit an entry at the moment.</b><br/>
                        {{ deadlineRange }}
                    </b-card>
                    <entry
                        v-else-if="(nodes[currentNode].type == 'd' || nodes[currentNode].type == 'e'
                            || nodes[currentNode].type == 'a') && currentTemplate"
                        ref="entry"
                        :class="{'input-disabled': !loadingNodes && journal.needs_lti_link.length > 0
                            && assignment.active_lti_course}"
                        :template="currentTemplate"
                        :assignment="assignment"
                        :node="nodes[currentNode]"
                        :create="nodes[currentNode].type == 'a' || (nodes[currentNode].type == 'd'
                            && !nodes[currentNode].entry)"
                        @entry-deleted="removeCurrentEntry"
                        @entry-posted="entryPosted"
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

            <h3 class="theme-h3">
                Actions
            </h3>

            <b-button
                v-if="!loadingNodes"
                v-b-modal="'journal-import-modal'"
                class="multi-form change-button full-width"
            >
                <icon name="file-import"/>
                Import Journal
            </b-button>

            <journal-import-modal
                v-if="!loadingNodes"
                modalID="journal-import-modal"
                :targetAssignmentID="Number(aID)"
            />

            <transition name="fade">
                <b-button
                    v-if="addIndex > -1 && currentNode !== addIndex"
                    class="fab"
                    @click="currentNode = addIndex"
                >
                    <icon
                        name="plus"
                        scale="1.5"
                    />
                </b-button>
            </transition>
        </b-col>
    </b-row>
</template>

<script>
import Entry from '@/components/entry/Entry.vue'
import timeline from '@/components/timeline/Timeline.vue'
import breadCrumb from '@/components/assets/BreadCrumb.vue'
import loadWrapper from '@/components/loading/LoadWrapper.vue'
import journalStartCard from '@/components/journal/JournalStartCard.vue'
import journalEndCard from '@/components/journal/JournalEndCard.vue'
import journalDetails from '@/components/journal/JournalDetails.vue'
import journalImportModal from '@/components/journal/JournalImportModal.vue'
import progressNode from '@/components/entry/ProgressNode.vue'

import journalAPI from '@/api/journal.js'
import assignmentAPI from '@/api/assignment.js'

export default {
    components: {
        breadCrumb,
        loadWrapper,
        timeline,
        Entry,
        progressNode,
        journalStartCard,
        journalEndCard,
        journalDetails,
        journalImportModal,
    },
    props: ['cID', 'aID', 'jID'],
    data () {
        return {
            currentNode: -1,
            nodes: [],
            journal: null,
            assignment: null,
            loadingNodes: true,
            selectedTemplate: null,
        }
    },
    computed: {
        addIndex () {
            return this.nodes.findIndex(node => node.type === 'a')
        },
        deadlineRange () {
            const unlockDate = this.$root.beautifyDate(this.nodes[this.currentNode].unlock_date)
            const lockDate = this.$root.beautifyDate(this.nodes[this.currentNode].lock_date)

            if (unlockDate && lockDate) {
                return `Available from ${unlockDate} until ${lockDate}`
            } else if (unlockDate) {
                return `Available from ${unlockDate}`
            } else if (lockDate) {
                return `Available until ${lockDate}`
            }

            return ''
        },
        currentNodeIsLocked () {
            const currentDate = new Date()
            let unlockDate = currentDate
            let lockDate = currentDate

            if (!this.nodes[this.currentNode]) {
                return false
            }

            if (this.nodes[this.currentNode].unlock_date) {
                unlockDate = new Date(this.nodes[this.currentNode].unlock_date)
            }

            if (this.nodes[this.currentNode].lock_date) {
                lockDate = new Date(this.nodes[this.currentNode].lock_date)
            }

            return currentDate < unlockDate || lockDate < currentDate
        },
        currentTemplate () {
            if (this.nodes[this.currentNode].entry && this.nodes[this.currentNode].entry.template) {
                // Existing entry.
                return this.nodes[this.currentNode].entry.template
            } else if (this.nodes[this.currentNode].template) {
                // Preset node.
                return this.nodes[this.currentNode].template
            } else if (this.nodes[this.currentNode].templates && this.nodes[this.currentNode].templates.length === 1) {
                // Add node with only one unlimited template available.
                return this.nodes[this.currentNode].templates[0]
            }

            // Add node with multiple choices: select from dropdown.
            return this.selectedTemplate
        },
    },
    created () {
        assignmentAPI.get(this.aID, this.cID, { customErrorToast: 'Error while loading assignment data.' })
            .then((assignment) => {
                this.assignment = assignment

                const initialCalls = []
                initialCalls.push(journalAPI.get(this.jID))

                if (!this.assignment.unlock_date || new Date(this.assignment.unlock_date) < new Date()) {
                    initialCalls.push(journalAPI.getNodes(this.jID))
                }
                Promise.all(initialCalls).then((results) => {
                    this.journal = results[0]
                    if (results.length > 1) {
                        this.nodes = results[1]
                        if (this.$route.query.nID !== undefined) {
                            this.currentNode = this.findEntryNode(parseInt(this.$route.query.nID, 10))
                        }
                    }
                    this.loadingNodes = false
                })
            })
    },
    methods: {
        removeCurrentEntry () {
            if (this.nodes[this.currentNode].type === 'd') {
                this.nodes[this.currentNode].entry = null
                this.currentNode = 0
            } else {
                this.nodes.splice(this.currentNode, 1)
            }
        },
        selectNode (selectedNode) {
            if (selectedNode !== this.currentNode || this.safeToLeave()) {
                this.currentNode = selectedNode
            }
        },
        entryPosted (data) {
            this.nodes = data.nodes
            this.loadingNodes = false
            this.currentNode = data.added
            this.selectedTemplate = null
        },
        findEntryNode (nodeID) {
            for (let i = 0; i < this.nodes.length; i++) {
                if (this.nodes[i].nID === nodeID) {
                    return i
                }
            }
            return 0
        },
        safeToLeave () {
            return !this.$refs.entry || this.$refs.entry.safeToLeave()
                || window.confirm('Progress will not be saved if you leave. Do you wish to continue?')
        },
    },
}
</script>

<style lang="sass">
.journal-details-card > .card-body
    padding-top: 45px
</style>
