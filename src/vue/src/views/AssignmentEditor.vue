<template>
    <timeline-layout>
        <template
            v-if="!loading"
            v-slot:left
        >
            <assignment-editor-bread-crumb
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
            <assignment-editor-bread-crumb
                v-if="$root.xl"
                v-intro="welcomeIntroText"
                v-intro-step="1"
                @start-tutorial="$intro().start()"
            />

            <load-wrapper :loading="loading">
                <assignment-editor-active-component-switch/>
            </load-wrapper>
        </template>

        <template
            v-if="!loading"
            v-slot:right
        >
            <template-menu
                v-intro="templateIntroText"
                v-intro-step="2"
            />

            <category-menu
                v-intro="categoryIntroText"
                v-intro-step="4"
            />
        </template>
    </timeline-layout>
</template>

<script>
import AssignmentEditorActiveComponentSwitch from
    '@/components/assignment_editor/AssignmentEditorActiveComponentSwitch.vue'
import AssignmentEditorBreadCrumb from '@/components/assignment_editor/AssignmentEditorBreadCrumb.vue'
import CategoryMenu from '@/components/category/CategoryMenu.vue'
import LoadWrapper from '@/components/loading/LoadWrapper.vue'
import TemplateMenu from '@/components/template/TemplateMenu.vue'
import TimelineLayout from '@/components/columns/TimelineLayout.vue'
import timeline from '@/components/timeline/Timeline.vue'

import { mapActions, mapGetters, mapMutations } from 'vuex'

export default {
    name: 'AssignmentEditor',
    components: {
        timeline,
        AssignmentEditorActiveComponentSwitch,
        AssignmentEditorBreadCrumb,
        CategoryMenu,
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
            // QUESTION: Should we stop using 'nodes' when talking about the timeline (user facing)?
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
            categoryIntroText: `
<i>Categories</i> can be linked to entries and be used to filter the timeline.<br/><br/>

You can choose to link specific templates to categories. When a student makes use of these templates
to create an entry, the category will be linked to the entry by default.<br/><br/>

Whether the student can edit which categories belong to an entry themselves, can be configured via the
respective template setting "<i>Fixed Categories / Custom Categories</i>".
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
            /* Start with the assignment details selected in read mode */
            this.timelineElementSelected({ timelineElementIndex: -1, mode: this.activeComponentModeOptions.read })
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
            reset: 'assignmentEditor/RESET',
        }),
        ...mapActions({
            confirmIfDirty: 'assignmentEditor/confirmIfDirty',
            timelineElementSelected: 'assignmentEditor/timelineElementSelected',
            assignmentRetrieve: 'assignment/retrieve',
            presetNodeList: 'presetNode/list',
            categoryList: 'category/list',
            templateList: 'template/list',
        }),
    },
    beforeRouteLeave (to, from, next) {
        this.confirmIfDirty()
            .then((confirmed) => {
                if (confirmed) {
                    this.$intro().exit()
                    this.reset()
                    next()
                } else {
                    next(false)
                }
            })
    },
}
</script>

<style lang="sass">
.menu-list-header
    border-bottom: 2px solid $theme-dark-grey

.menu-item-link
    padding: 5px
    border-bottom: 1px solid $theme-dark-grey
    cursor: pointer
    vertical-align: middle
    svg
        margin-top: 3px
    .max-one-line
        width: calc(100% - 2em)
    .edit-icon
        margin-top: 4px
    .edit-icon, .trash-icon
        width: 0px
        visibility: hidden
    &:hover
        background-color: $theme-medium-grey
        .max-one-line
            width: calc(100% - 5em)
        .edit-icon, .trash-icon
            visibility: visible
            width: auto
    &.active
        background-color: $theme-light-grey
</style>
