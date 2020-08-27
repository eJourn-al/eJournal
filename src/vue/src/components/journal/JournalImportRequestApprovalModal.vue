<template>
    <b-modal
        :id="modalID"
        :ref="modalID"
        size="lg"
        :title="(autoShow) ? 'This journal has outstanding import requests' : 'Manage Import Requests'"
        hideFooter
        noEnforceFocus
        @hide="updateJIRModalDisplayPreferences"
    >
        <b-card class="no-hover">
            <h2 class="theme-h2 multi-form">
                Select an import request
            </h2>

            <p>
                An approved import request will add all entries to the timeline and copy any related comments. Any
                imported entries will be flagged as "<i>imported</i>".
            </p>

            <load-wrapper
                :loading="loading"
            >
                <div v-if="assignments && assignments.length > 0">
                    <theme-select
                        v-model="selectedAssignment"
                        label="name"
                        trackBy="id"
                        :options="assignments"
                        :multiple="false"
                        :searchable="true"
                        placeholder="Select An Assignment"
                        class="multi-form"
                    />

                    <journal-card
                        v-if="selectedJir"
                        v-b-tooltip.hover="'Navigate to journal in full'"
                        :journal="selectedJir.source.journal"
                        :assignment="selectedJir.source.assignment"
                        @click.native="openSelectedJirInNewWindow()"
                    />

                    <hr/>

                    <dropdown-button
                        v-if="$hasPermission('can_grade')"
                        :up="true"
                        :selectedOption="$store.getters['preferences/journalImportRequestButtonSetting']"
                        :options="{
                            AIG: {
                                text: 'Approve including grades',
                                icon: 'paper-plane',
                                class: 'add-button',
                            },
                            AEG: {
                                text: 'Approve excluding grades',
                                icon: 'paper-plane',
                                class: 'add-button',
                            },
                            AWGZ: {
                                text: 'Approve with grades zeroed',
                                icon: 'paper-plane',
                                class: 'change-button',
                            },
                            DEC: {
                                text: 'Decline',
                                icon: 'ban',
                                class: 'delete-button',
                            },
                        }"
                        class="float-right"
                        :class="{ 'input-disabled': !selectedAssignment }"
                        @change-option="$store.commit('preferences/SET_JOURNAL_IMPORT_REQUEST_BUTTON_SETTING', $event)"
                        @click="handleJIR(selectedJir)"
                    />
                </div>

                <div v-else>
                    <h4 class="theme-h4">
                        No outstanding journal import requests available.
                    </h4>
                </div>
            </load-wrapper>
        </b-card>
    </b-modal>
</template>

<script>
import loadWrapper from '@/components/loading/LoadWrapper.vue'
import journalCard from '@/components/assignment/JournalCard.vue'
import dropdownButton from '@/components/assets/DropdownButton.vue'

import journalImportRequestAPI from '@/api/journal_import_request.js'

export default {
    components: {
        loadWrapper,
        journalCard,
        dropdownButton,
    },
    props: {
        modalID: {
            required: true,
            type: String,
        },
    },
    data () {
        return {
            jirs: [],
            selectedAssignment: null,
            loading: true,
            jirAction: null,
        }
    },
    computed: {
        // QUESTION:
        // How to simply provide jirs as options to the multiselect with a display for jir.source.assignment.name?
        assignments () {
            const arr = []
            this.jirs.forEach(jir => arr.push({
                name: `${jir.source.assignment.name}, ${this.getCourseName(jir.source.assignment.course)}`,
                id: jir.id,
                jir,
            }))
            return arr
        },
        selectedJir () {
            return (this.selectedAssignment ? this.selectedAssignment.jir : null)
        },
        autoShow () {
            return this.jirs.some(jir => !this.$store.getters['preferences/dismissedJIRs'].includes(jir.id))
        },
    },
    created () {
        journalImportRequestAPI.list(this.$route.params.jID).then((jirs) => {
            this.jirs = jirs
            if (jirs.length === 1) { this.selectedAssignment = { jir: jirs[0], name: jirs[0].target.assignment.name } }
            this.loading = false

            if (this.autoShow) {
                this.$root.$emit('bv::show::modal', this.modalID)
            }
        })
    },
    methods: {
        jirToJournalUrl (jir) {
            return `${window.location.protocol}//${window.location.host}/Home/`
                + `Course/${jir.source.assignment.course.id}/`
                + `Assignment/${jir.source.assignment.id}/`
                + `Journal/${jir.source.journal.id}`
        },
        handleJIR (jir) {
            // TODO JIR: Update timeline without required reload
            journalImportRequestAPI.update(
                jir.id,
                this.$store.getters['preferences/journalImportRequestButtonSetting'],
                { responseSuccessToast: true },
            ).then(() => {
                this.$delete(this.jirs, this.jirs.findIndex(elem => elem.id === jir.id))
                if (this.jirs.length === 1) {
                    this.selectedAssignment = { name: this.jirs[0].source.assignment.name, jir: this.jirs[0] }
                }
                if (this.jirs.length === 0) {
                    this.selectedAssignment = null
                    this.$root.$emit('bv::hide::modal', this.modalID)
                }
            })
        },
        openSelectedJirInNewWindow () {
            window.open(this.jirToJournalUrl(this.selectedJir), '_blank')
        },
        updateJIRModalDisplayPreferences (event) {
            /*
             * The modal was closed by the user, other events are stuff like backdrop click or cross click on the modal
             * If it was an event, it was closed programatically, e.g. when there are simply no more jirs to process.
             */
            if (event.trigger !== 'event') {
                this.$store.commit('preferences/ADD_DISMISSED_JIRS_TO_JOURNAL', Array.from(this.jirs, jir => jir.id))
            }
        },
        getCourseName (course) {
            let name = course.name
            if (course.startdate) {
                name += ' ('
                name += course.startdate.substring(0, 4)
                if (course.enddate) {
                    name += ` - ${course.enddate.substring(0, 4)}`
                }
                name += ')'
            }
            return name
        },
    },
}
</script>
