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
                class="mb-3"
            />

            <category-menu
                v-intro="categoryIntroText"
                v-intro-step="4"
                class="mb-3"
            />

            <assignment-editor-danger-zone/>
        </template>
    </timeline-layout>
</template>

<script>
import AssignmentEditorActiveComponentSwitch from
    '@/components/assignment_editor/AssignmentEditorActiveComponentSwitch.vue'
import AssignmentEditorDangerZone from '@/components/assignment_editor/AssignmentEditorDangerZone.vue'
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
        AssignmentEditorDangerZone,
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

This is where you configure the structure of your assignment. Proceed with this tutorial to learn more.
`,
            templateIntroText: `
Customizable <i>templates</i> provide structure to students' journal entries.
You can choose from a wide range of content options: rich text, images, video embeds and many more.<br/><br/>

An individual template can be made available for <i>unlimited</i> use, or exclusively for specific deadlines.
`,
            timelineIntroText: `
When students add new entries to their journal, they will appear in the <i>timeline</i>.
A preview is shown here, where you can also configure assignment details such as the assignment due date.<br/><br/>

In the assignment editor, you can define deadlines as students progress throughout their journal:<br/><br/>
<b>Entry deadlines</b> represent an existing template which has to be completed.<br/>
<b>Progress goals</b> are intermediate point targets that have to be achieved.<br/><br/>

New deadlines can be added via the '+' button in the timeline.
`,
            categoryIntroText: `
Create custom <i>categories</i> that can be associated with templates or entries to allow easy filtering of a journal's
contents.<br/><br/>

Categories can also provide additional information for students, such as relevant learning objectives or skills.
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

.menu-item-link
    padding: 5px 10px
    border-bottom: 1px solid $border-color
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
            width: calc(100% - 3em)
        .edit-icon, .trash-icon
            visibility: visible
            width: auto
    &.active
        font-weight: bold
</style>
