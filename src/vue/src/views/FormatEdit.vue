<template>
    <load-wrapper :loading="loading">
        <timeline-layout>
            <template v-slot:left>
                <format-bread-crumb
                    v-if="$root.lgMax"
                    v-intro="welcomeIntroText"
                    v-intro-step="1"
                    @start-tutorial="$intro().start()"
                />

                <timeline
                    v-intro="timelineIntroText"
                    v-intro-step="3"
                    :selected="activeTimelineElementIndex"
                    :nodes="presetNodes"
                    :assignment="assignment"
                    :edit="true"
                    @select-node="(timelineElementIndex) => {
                        timelineElementSelected({ timelineElementIndex, mode: activeComponentModeOptions.read }) }
                    "
                />
            </template>

            <template v-slot:center>
                <format-bread-crumb
                    v-if="$root.xl"
                    v-intro="welcomeIntroText"
                    v-intro-step="1"
                    @start-tutorial="$intro().start()"
                />

                <format-active-components/>
            </template>

            <template v-slot:right>
                <template-menu
                    v-intro="templateIntroText"
                    v-intro-step="2"
                />

                <format-actions/>
            </template>
        </timeline-layout>
    </load-wrapper>
</template>

<script>
import FormatActions from '@/components/format/FormatActions.vue'
import FormatActiveComponents from '@/components/format/FormatActiveComponents.vue'
import FormatBreadCrumb from '@/components/format/FormatBreadCrumb.vue'
import LoadWrapper from '@/components/loading/LoadWrapper.vue'
import TemplateMenu from '@/components/template/TemplateMenu.vue'
import TimelineLayout from '@/components/columns/TimelineLayout.vue'
import timeline from '@/components/timeline/Timeline.vue'

import { mapActions, mapGetters, mapMutations } from 'vuex'

export default {
    name: 'FormatEdit',
    components: {
        timeline,
        FormatActions,
        FormatActiveComponents,
        FormatBreadCrumb,
        LoadWrapper,
        TemplateMenu,
        TimelineLayout,
    },
    data () {
        return {
            welcomeIntroText: `
Welcome to the assignment editor!<br/><br/>

This is where you can configure the structure of your assignment. Proceed with this tutorial to learn more.
`,
            templateIntroText: `
Every assignment contains customizable <i>templates</i> which specify what the contents of each journal entry should be.
There are two different types of templates:<br/><br/>

<ul>
    <li><b>Unlimited templates</b> can be freely used by students as often as they want</li>
    <li><b>Preset-only templates</b> can be used only for preset entries that you add to the timeline</li>
</ul><br/>

You can preview and edit a template by clicking on it.
`,
            timelineIntroText: `
The timeline forms the basis for an assignment. The name, due date and other details
of the assignment can also be changed here, by clicking the first node.<br/><br/>

The timeline contains a node for every entry. You can add two different types of nodes to it:<br/><br/>
<ul>
    <li><b>Preset entries</b> are entries with a specific template which have to be completed before a set deadline</li>
    <li><b>Progress goals</b> are point targets that have to be met before a set deadline</li>
</ul><br/>

New nodes can be added via the '+' node. Click any node to view its contents.
`,
            loading: true,
        }
    },
    computed: {
        ...mapGetters({
            assignment: 'assignment/assignment',
            activeComponentMode: 'assignmentEditor/activeComponentMode',
            activeComponentModeOptions: 'assignmentEditor/activeComponentModeOptions',
            activeComponent: 'assignmentEditor/activeComponent',
            activeComponentOptions: 'assignmentEditor/activeComponentOptions',
            selectedTimelineElementIndex: 'assignmentEditor/selectedTimelineElementIndex',
            presetNodes: 'presetNode/assignmentPresetNodes',
            savedPreferences: 'preferences/saved',
        }),
        activeTimelineElementIndex () {
            if (this.activeComponent === this.activeComponentOptions.timeline) {
                return this.selectedTimelineElementIndex
            }

            return null
        },
    },
    created () {
        const init = [
            this.assignmentRetrieve({ id: this.$route.params.aID }),
            this.presetNodeList({ aID: this.$route.params.aID }),
            this.categoryList({ aID: this.$route.params.aID }),
            this.templateList({ aID: this.$route.params.aID }),
        ]

        Promise.all(init).then(() => {
            this.loading = false

            if (this.savedPreferences.show_format_tutorial) {
                this.changePreference({ show_format_tutorial: false })
                this.$intro().start()
            }
        })
    },
    methods: {
        ...mapMutations({
            changePreference: 'preferences/CHANGE_PREFERENCES',
        }),
        ...mapActions({
            timelineElementSelected: 'assignmentEditor/timelineElementSelected',
            assignmentRetrieve: 'assignment/retrieve',
            presetNodeList: 'presetNode/list',
            categoryList: 'category/list',
            templateList: 'template/list',
        }),
    },
    // Question: Should a warning be given if any changes are unsaved?
    // E.g. drafts exist?
    // All modifications remain untill the user switches assignment route or closes the tab
    beforeRouteLeave (to, from, next) {
        this.$intro().exit()
        next()
    },
}
</script>

<style lang="sass">
.template-list-header
    border-bottom: 2px solid $theme-dark-grey
</style>
