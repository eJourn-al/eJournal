<template>
    <timeline-layout>
        <template #left>
            <bread-crumb v-if="$root.lgMax">
                <template v-if="!loadingNodes && assignment.is_group_assignment">
                    - {{ journal.name }}
                </template>
            </bread-crumb>
            <timeline
                v-if="!loadingNodes"
                :nodes="nodes"
                :assignment="assignment"
            />
        </template>

        <template #center>
            <bread-crumb v-if="$root.xl">
                <template v-if="!loadingNodes && assignment.is_group_assignment">
                    - {{ journal.name }}
                </template>
            </bread-crumb>

            <user-missing-lti-link-warning
                v-if="!loadingNodes && journal.needs_lti_link.length > 0 && assignment.active_lti_course"
                :assignment="assignment"
                :journal="journal"
            />

            <load-wrapper :loading="loadingNodes">
                <template v-if="currentNode.type === addNodeSymbol">
                    <h4 class="theme-h4 mb-2 d-block">
                        <span>New entry</span>
                    </h4>
                    <b-form-select
                        v-if="currentNode.templates.length > 1"
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
                            v-for="template in currentNode.templates"
                            :key="template.id"
                            :value="template"
                        >
                            {{ template.name }}
                        </option>
                    </b-form-select>
                </template>

                <journal-start-card
                    v-if="currentNode === startNode"
                    :assignment="assignment"
                />
                <journal-end-card
                    v-else-if="currentNode === endNode"
                    :assignment="assignment"
                />
                <progress-node
                    v-else-if="currentNode.type == 'p'"
                    :currentNode="currentNode"
                    :nodes="nodes"
                    :bonusPoints="journal.bonus_points"
                />
                <b-card
                    v-else-if="currentNode.type == 'd' && !currentNode.entry
                        && currentNodeIsLocked"
                    :class="$root.getBorderClass($route.params.cID)"
                    class="no-hover"
                >
                    <h2 class="theme-h2 mb-2">
                        {{ currentNode.template.name }}
                    </h2>
                    <hr class="full-width"/>
                    <b>This preset is locked. You cannot submit an entry at the moment.</b><br/>
                    {{ deadlineRange }}
                </b-card>
                <entry
                    v-else-if="currentTemplate && ['d', 'e', 'a'].includes(currentNode.type)"
                    ref="entry"
                    :class="{'input-disabled': !loadingNodes && journal.needs_lti_link.length > 0
                        && assignment.active_lti_course}"
                    :template="currentTemplate"
                    :assignment="assignment"
                    :node="currentNode"
                    :create="currentNode.type == 'a' || (currentNode.type == 'd' && !currentNode.entry)"
                    @entry-deleted="removeCurrentEntry"
                    @entry-posted="entryPosted"
                />
            </load-wrapper>
        </template>

        <template #right>
            <h3 class="theme-h3">
                Details
            </h3>
            <b-card
                :class="$root.getBorderClass($route.params.cID)"
                class="journal-details-card no-hover mb-3"
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
                class="multi-form orange-button full-width"
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
                    v-if="addNodeExists && currentNode.type !== addNodeSymbol"
                    class="fab"
                    @click="setCurrentNode(nodes.find((node) => node.type === addNodeSymbol))"
                >
                    <icon
                        name="plus"
                        scale="1.5"
                    />
                </b-button>
            </transition>
        </template>
    </timeline-layout>
</template>

<script>
import Entry from '@/components/entry/Entry.vue'
import TimelineLayout from '@/components/columns/TimelineLayout.vue'
import UserMissingLtiLinkWarning from '@/components/journal/UserMissingLtiLinkWarning.vue'

import breadCrumb from '@/components/assets/BreadCrumb.vue'
import journalDetails from '@/components/journal/JournalDetails.vue'
import journalEndCard from '@/components/journal/JournalEndCard.vue'
import journalImportModal from '@/components/journal/JournalImportModal.vue'
import journalStartCard from '@/components/journal/JournalStartCard.vue'
import loadWrapper from '@/components/loading/LoadWrapper.vue'
import progressNode from '@/components/entry/ProgressNode.vue'
import timeline from '@/components/timeline/Timeline.vue'

import assignmentAPI from '@/api/assignment.js'
import journalAPI from '@/api/journal.js'

import { mapGetters, mapMutations } from 'vuex'

export default {
    components: {
        breadCrumb,
        loadWrapper,
        timeline,
        Entry,
        TimelineLayout,
        progressNode,
        journalStartCard,
        journalEndCard,
        journalDetails,
        journalImportModal,
        UserMissingLtiLinkWarning,
    },
    props: ['cID', 'aID', 'jID'],
    data () {
        return {
            nodes: [],
            journal: null,
            assignment: null,
            loadingNodes: true,
            selectedTemplate: null,
        }
    },
    computed: {
        ...mapGetters({
            currentNode: 'timeline/currentNode',
            startNode: 'timeline/startNode',
            addNodeSymbol: 'timeline/addNodeSymbol', // Add node is serialized by the backend
            endNode: 'timeline/endNode',
        }),
        addNodeExists () {
            return this.nodes.findIndex((node) => node.type === this.addNodeSymbol) !== -1
        },
        deadlineRange () {
            const unlockDate = this.$root.beautifyDate(this.currentNode.unlock_date)
            const lockDate = this.$root.beautifyDate(this.currentNode.lock_date)

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

            if (!this.currentNode) {
                return false
            }

            if (this.currentNode.unlock_date) {
                unlockDate = new Date(this.currentNode.unlock_date)
            }

            if (this.currentNode.lock_date) {
                lockDate = new Date(this.currentNode.lock_date)
            }

            return currentDate < unlockDate || lockDate < currentDate
        },
        currentTemplate () {
            if (this.currentNode.entry && this.currentNode.entry.template) {
                // Existing entry.
                return this.currentNode.entry.template
            } else if (this.currentNode.template) {
                // Preset node.
                return this.currentNode.template
            } else if (this.currentNode.templates && this.currentNode.templates.length === 1) {
                // Add node with only one unlimited template available.
                return this.currentNode.templates[0]
            }

            // Add node with multiple choices: select from dropdown.
            return this.selectedTemplate
        },
    },
    created () {
        this.setCurrentNode(this.startNode)
        this.pushNodeNavigationGuard(this.safeToLeave)

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
                            const nID = parseInt(this.$route.query.nID, 10)
                            const nodeToSelect = this.nodes.find((node) => node.id === nID)
                            this.setCurrentNode(nodeToSelect || this.startNode)
                        }
                    }
                    this.loadingNodes = false
                })
            })
    },
    beforeDestroy () {
        this.removeNodeNavigationGuard(this.safeToLeave)
    },
    methods: {
        ...mapMutations({
            setCurrentNode: 'timeline/SET_CURRENT_NODE',
            pushNodeNavigationGuard: 'timeline/PUSH_NODE_NAVIGATION_GUARD',
            removeNodeNavigationGuard: 'timeline/REMOVE_NODE_NAVIGATION_GUARD',
        }),
        removeCurrentEntry () {
            if (this.currentNode.type === 'd') {
                this.currentNode.entry = null
            } else {
                this.nodes = this.nodes.filter((node) => node !== this.currentNode)
            }

            this.setCurrentNode(this.startNode)
        },
        entryPosted (data) {
            this.nodes = data.nodes
            this.loadingNodes = false
            this.setCurrentNode(this.nodes[data.added])
            this.selectedTemplate = null
        },
        safeToLeave () {
            return (
                !this.$refs.entry
                || this.$refs.entry.safeToLeave()
                || window.confirm('Progress will not be saved if you leave. Do you wish to continue?')
            )
        },
    },
}
</script>

<style lang="sass">
.journal-details-card > .card-body
    padding-top: 45px
</style>
