<template>
    <b-modal
        :id="modalID"
        :ref="modalID"
        size="lg"
        :title="(autoShow) ? 'This journal has outstanding import requests' : 'Manage Import Requests'"
        noEnforceFocus
        @hide="updateJIRModalDisplayPreferences"
    >
        <p>
            The author of this journal has requested to import content from another journal.
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
                    class="mb-2"
                />

                <journal-card
                    v-if="selectedJir"
                    v-b-tooltip.hover="'Navigate to original journal'"
                    :journal="selectedJir.source.journal"
                    :assignment="selectedJir.source.assignment"
                    :openInNewTab="true"
                />
            </div>

            <div v-else>
                <b>No outstanding journal import requests.</b>
            </div>
        </load-wrapper>
        <dropdown-button
            v-if="!loading && $hasPermission('can_grade') && assignments && assignments.length > 0"
            slot="modal-footer"
            :up="true"
            :selectedOption="$store.getters['preferences/journalImportRequestButtonSetting']"
            :options="{
                AIG: {
                    text: 'Approve including grades',
                    icon: 'check',
                    class: 'green-button',
                },
                AEG: {
                    text: 'Approve excluding grades',
                    icon: 'check',
                    class: 'green-button',
                },
                AWGZ: {
                    text: 'Approve with grades zeroed',
                    icon: 'check',
                    class: 'orange-button',
                },
                DEC: {
                    text: 'Decline',
                    icon: 'times',
                    class: 'red-button',
                },
            }"
            class="float-right"
            :class="{ 'input-disabled': !selectedAssignment || jirPatchInFlight }"
            @change-option="$store.commit('preferences/SET_JOURNAL_IMPORT_REQUEST_BUTTON_SETTING', $event)"
            @click="handleJIR(selectedJir)"
        />
    </b-modal>
</template>

<script>
import dropdownButton from '@/components/assets/DropdownButton.vue'
import journalCard from '@/components/assignment/JournalCard.vue'
import loadWrapper from '@/components/loading/LoadWrapper.vue'
import utils from '@/utils/generic_utils.js'

import jirAPI from '@/api/journal_import_request.js'

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
            jirPatchInFlight: false,
        }
    },
    computed: {
        assignments () {
            const arr = []
            this.jirs.forEach((jir) => arr.push({
                name: `${utils.assignmentWithDatesDisplay(jir.source.assignment)}, ${utils.courseWithDatesDisplay(
                    jir.source.assignment.course)}`,
                id: jir.id,
                jir,
            }))
            return arr
        },
        selectedJir () {
            return (this.selectedAssignment ? this.selectedAssignment.jir : null)
        },
        autoShow () {
            return this.jirs.some((jir) => !this.$store.getters['preferences/dismissedJIRs'].includes(jir.id))
        },
    },
    created () {
        jirAPI.list(this.$route.params.jID).then((jirs) => {
            this.jirs = jirs
            if (jirs.length === 1) {
                this.selectedAssignment = {
                    jir: jirs[0],
                    name: `${jirs[0].source.assignment.name}, `
                        + `${utils.courseWithDatesDisplay(jirs[0].source.assignment.course)}`,
                }
            }
            this.loading = false

            if (this.autoShow) {
                this.$root.$emit('bv::show::modal', this.modalID)
            }
        })
    },
    methods: {
        handleJIR (jir) {
            this.jirPatchInFlight = true
            jirAPI.update(
                jir.id,
                this.$store.getters['preferences/journalImportRequestButtonSetting'],
                { responseSuccessToast: true },
            ).then(() => {
                this.$delete(this.jirs, this.jirs.findIndex((elem) => elem.id === jir.id))
                if (this.jirs.length === 1) {
                    this.selectedAssignment = {
                        jir: this.jirs[0],
                        name: `${this.jirs[0].target.assignment.name}, `
                            + `${utils.courseWithDatesDisplay(this.jirs[0].source.assignment.course)}`,
                    }
                }
                if (this.jirs.length === 0) {
                    this.selectedAssignment = null
                    this.$root.$emit('bv::hide::modal', this.modalID)
                }
                this.$emit('jir-processed')
            }).finally(() => {
                this.jirPatchInFlight = false
            })
        },
        updateJIRModalDisplayPreferences (event) {
            /*
             * The modal was closed by the user, other events are stuff like backdrop click or cross click on the modal
             * If it was an event, it was closed programatically, e.g. when there are simply no more jirs to process.
             */
            if (event.trigger !== 'event') {
                this.$store.commit('preferences/ADD_DISMISSED_JIRS_TO_JOURNAL', Array.from(this.jirs, (jir) => jir.id))
            }
        },
    },
}
</script>
