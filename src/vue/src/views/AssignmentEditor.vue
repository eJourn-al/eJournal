<template>
    <timeline-layout>
        <template
            v-if="!loading"
            v-slot:left
        >
            <bread-crumb
                v-if="$root.lgMax"
                v-intro="welcomeIntroText"
                v-intro-step="1"
            >
                <icon
                    v-intro="finishedIntroText"
                    v-intro-step="5"
                    v-b-tooltip:hover="'Click to start a tutorial for this page'"
                    name="info-circle"
                    scale="1.75"
                    class="info-icon shift-up-5 ml-1"
                    @click.native.stop="$intro().start()"
                />
            </bread-crumb>

            <timeline
                v-intro="timelineIntroText"
                v-intro-step="3"
                :nodes="presetNodes"
                :assignment="assignment"
            />
        </template>

        <template v-slot:center>
            <bread-crumb
                v-if="$root.xl"
                v-intro="welcomeIntroText"
                v-intro-step="1"
            >
                <icon
                    v-intro="finishedIntroText"
                    v-intro-step="5"
                    v-b-tooltip:hover="'Click to start a tutorial for this page'"
                    name="info-circle"
                    scale="1.75"
                    class="info-icon shift-up-5 ml-1"
                    @click.native.stop="$intro().start()"
                />
            </bread-crumb>

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
import BreadCrumb from '@/components/assets/BreadCrumb.vue'
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
        BreadCrumb,
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
            timelineIntroText: `
The timeline forms the basis for an assignment. The name, due date and other details
of the assignment can also be changed here, by clicking on <i>"Assignment details"</i>.<br/><br/>

The timeline presents an overview of all entries made by a student. In the assignment editor, it is possible to set
specific deadlines, two types exist:<br/><br/>
<ul>
    <li><b>Preset entries</b> are entries with a specific template which have to be completed before a set deadline</li>
    <li><b>Progress goals</b> are point targets that have to be met before a set deadline</li>
</ul><br/>

New deadlines can be added via the '+' button in the timeline. Click any deadline to view its contents.
`,
            categoryIntroText: `
<i>Categories</i> can be linked to entries and be used to filter the timeline.<br/><br/>

You can choose to link specific templates to categories. When a student makes use of these templates
to create an entry, the category will be linked to the entry by default.<br/><br/>

It is possible to allow students to configure which categories belong to an entry. This can be enabled
via the respective template setting "<i>Fixed Categories / Custom Categories</i>".
`,
            finishedIntroText: `
That's it! If you have any more questions, do not hesitate to contact us via the support button at the bottom of
any page.<br/><br/>

This tutorial can be consulted again by clicking the <i>info</i> sign.
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
            presetNodes: 'presetNode/assignmentPresetNodes',
            savedPreferences: 'preferences/saved',
            currentNode: 'timeline/currentNode',
            startNode: 'timeline/startNode',
        }),
    },
    watch: {
        /* Observe timeline UI navigation */
        currentNode (element) {
            if (element) {
                this.timelineElementSelected({ element })
            }
        },
        /* If the active component is not the timeline, ensure no timeline UI element is highlighted */
        activeComponent (val) {
            if (val !== this.activeComponentOptions.timeline && this.currentNode) {
                this.setCurrentNode(null)
            }
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
            this.setCurrentNode(this.startNode)
            this.timelineElementSelected({ element: this.startNode, mode: this.activeComponentModeOptions.read })
            this.loading = false

            if (this.savedPreferences.show_format_tutorial) {
                this.changePreference({ show_format_tutorial: false })
                this.$nextTick(() => { this.$intro().start() })
            }
        })
    },
    methods: {
        ...mapMutations({
            changePreference: 'preferences/CHANGE_PREFERENCES',
            reset: 'assignmentEditor/RESET',
            setCurrentNode: 'timeline/SET_CURRENT_NODE',
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
.dirty::after
    content: '\2022'
    font-size: 2em
    line-height: 10px
    vertical-align: middle
    margin-left: 4px
    margin-right: 4px
    color: $theme-orange
    text-shadow: 0 0 6px rgba(232,167,35,0.5), 0 0 6px rgba(232,167,35,0.8)

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
