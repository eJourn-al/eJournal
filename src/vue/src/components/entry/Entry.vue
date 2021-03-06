<template>
    <div>
        <b-card>
            <template slot="header">
                <template v-if="!(edit || create)">
                    <span
                        v-if="gradePublished"
                        class="float-right"
                    >
                        Grade: <b>{{ node.entry.grade.grade }}</b>
                    </span>
                    <span
                        v-else-if="!node.entry.editable"
                        class="float-right"
                    >
                        Grade:
                        <icon
                            v-b-tooltip.hover="'Awaiting grade.'"
                            name="hourglass-half"
                            class="shift-up-2"
                        />
                    </span>
                    <template v-else-if="node.entry.editable">
                        <b-button
                            class="ml-2 grey-button float-right"
                            @click="edit = true"
                        >
                            <icon name="edit"/>
                            Edit
                        </b-button>
                        <b-button
                            v-if="node.entry.is_draft"
                            class="ml-2 red-button float-right"
                            @click="() => deleteEntry(true)"
                        >
                            <icon name="trash"/>
                            Discard draft
                        </b-button>
                        <b-button
                            v-else
                            class="ml-2 red-button float-right"
                            @click="() => deleteEntry(false)"
                        >
                            <icon name="trash"/>
                            Delete
                        </b-button>
                    </template>
                </template>
                <b-button
                    v-if="edit"
                    class="ml-2 red-button float-right"
                    @click="clearDraft()"
                >
                    <icon name="ban"/>
                    Cancel
                </b-button>

                <entry-title
                    :template="template"
                    :node="node"
                />
                <div
                    v-if="!(edit || create)"
                    class="small"
                >
                    Posted
                    <timeago
                        v-b-tooltip.hover="$root.beautifyDate(node.entry.creation_date)"
                        :datetime="node.entry.creation_date"
                    />
                    by {{ node.entry.author }}
                    <icon
                        v-if="(new Date(node.entry.last_edited).getTime() - new Date(node.entry.creation_date)
                            .getTime()) / 1000 > 180"
                        v-b-tooltip.hover="`Last edited ${$root.beautifyDate(node.entry.last_edited)} by
                            ${node.entry.last_edited_by}`"
                        class="ml-1 fill-grey"
                        scale="0.8"
                        name="history"
                    />
                    <br/>
                    <b-badge
                        v-if="node.due_date
                            && new Date(node.due_date) < new Date(node.entry.last_edited)"
                        v-b-tooltip:hover="'This entry was posted after the due date'"
                        pill
                        class="late-submission-badge mr-2"
                    >
                        LATE
                    </b-badge>
                    <b-badge
                        v-if="node.entry.jir"
                        v-b-tooltip:hover="
                            `This entry has been imported from the assignment
                            ${node.entry.jir.source.assignment.name}
                            (${node.entry.jir.source.assignment.course.abbreviation}), approved by
                            ${node.entry.jir.processor.full_name}`"
                        pill
                        class="imported-entry-badge mr-2"
                    >
                        IMPORTED
                    </b-badge>
                </div>
            </template>

            <sandboxed-iframe
                v-if="node && node.description"
                :content="node.description"
            />
            <files-list
                v-if="node && node.attached_files && node.attached_files.length > 0"
                :files="node.attached_files"
                class="mr-2 mb-2 align-top"
            />
            <deadline-date-display
                v-if="node && node.type === 'd' && (edit || create)"
                :subject="node"
                class="mb-2 align-top"
            />

            <b-form-group v-if="node && template.allow_custom_title && (edit || create)">
                <template #label>
                    Title
                    <tooltip tip="The title will also be displayed in the timeline."/>
                </template>

                <sandboxed-iframe
                    v-if="template.title_description"
                    :content="template.title_description"
                />

                <b-input
                    v-model="title"
                />
            </b-form-group>

            <entry-fields
                :template="template"
                :content="newEntryContent"
                :edit="edit || create"
                :nodeID="node ? node.id : -1"
                @uploading-file="uploadingFiles ++"
                @finished-uploading-file="uploadingFiles --"
            />

            <entry-categories
                :id="`entry-${(create) ? Math.random() : node.entry.id}-categories`"
                :create="create"
                :edit="edit"
                :entry="(create) ? newEntryContent : node.entry"
                :template="template"
                class="mr-2 mt-2 align-top"
            />
            <deadline-date-display
                v-if="node && node.type === 'd' && !(edit || create)"
                :subject="node"
                class="mt-2 align-top"
            />

            <template
                v-if="edit || create"
                #footer
            >
                <dropdown-button
                    v-if="edit"
                    :selectedOption="draftPostEntrySetting"
                    :options="{
                        p: {
                            text: 'Post',
                            icon: 'paper-plane',
                            class: 'green-button',
                        },
                        d: {
                            text: 'Save as draft',
                            icon: 'save',
                            class: 'gray-button',
                            tooltip: 'This will also hide the entry from the teacher(s)'
                        },
                    }"
                    :class="{ 'input-disabled': requestInFlight || uploadingFiles > 0 }"
                    :up="true"
                    class="float-right"
                    @change-option="(e) => draftPostEntrySetting = e"
                    @click="() => saveChanges(isDraft = draftPostEntrySetting === 'd')"
                />

                <dropdown-button
                    v-else-if="create"
                    :selectedOption="draftPostEntrySetting"
                    :options="{
                        p: {
                            text: 'Post',
                            icon: 'paper-plane',
                            class: 'green-button',
                        },
                        d: {
                            text: 'Save as draft',
                            icon: 'save',
                            class: 'gray-button',
                            tooltip: 'This will also hide the entry from the teacher(s)'
                        },
                    }"
                    :class="{ 'input-disabled': requestInFlight || uploadingFiles > 0 }"
                    :up="true"
                    class="float-right"
                    @change-option="(e) => draftPostEntrySetting = e"
                    @click="() => createEntry(isDraft = draftPostEntrySetting === 'd')"
                />
            </template>
        </b-card>
        <comments
            v-if="node && node.entry"
            :eID="node.entry.id"
        />
    </div>
</template>

<script>
import Comments from '@/components/entry/Comments.vue'
import DeadlineDateDisplay from '@/components/assets/DeadlineDateDisplay.vue'
import DropdownButton from '@/components/assets/DropdownButton.vue'
import EntryCategories from '@/components/category/EntryCategories.vue'
import EntryFields from '@/components/entry/EntryFields.vue'
import EntryTitle from '@/components/entry/EntryTitle.vue'
import SandboxedIframe from '@/components/assets/SandboxedIframe.vue'
import Tooltip from '@/components/assets/Tooltip.vue'
import filesList from '@/components/assets/file_handling/FilesList.vue'

import entryAPI from '@/api/entry.js'

export default {
    components: {
        DeadlineDateDisplay,
        Comments,
        DropdownButton,
        EntryFields,
        EntryTitle,
        SandboxedIframe,
        Tooltip,
        filesList,
        EntryCategories,
    },
    props: {
        template: {
            required: true,
        },
        node: {
            required: false,
            default: null,
        },
        create: {
            default: false,
        },
        startInEdit: {
            default: false,
        },
    },
    data () {
        return {
            edit: this.startInEdit,
            requestInFlight: false,
            newEntryContent: Object(),
            title: null,
            uploadingFiles: 0,
            draftPostEntrySetting: 'p',
        }
    },
    computed: {
        gradePublished () {
            return this.node.entry && this.node.entry.grade && this.node.entry.grade.published
        },
    },
    watch: {
        node: {
            immediate: true,
            handler () {
                this.clearDraft()
                this.edit = this.startInEdit
            },
        },
        template: {
            immediate: true,
            handler () {
                // Add node should empty filled in entry content when switching template
                if (this.node.type === 'a') {
                    this.newEntryContent = Object()
                    this.title = ''
                }
            },
        },
    },
    methods: {
        saveChanges (isDraft = false) {
            if (isDraft || this.checkRequiredFields()) {
                this.requestInFlight = true
                entryAPI.update(
                    this.node.entry.id,
                    {
                        content: this.newEntryContent,
                        title: this.template.allow_custom_title ? this.title : null,
                        is_draft: isDraft,
                    },
                    { customSuccessToast: 'Entry successfully updated.' },
                )
                    .then((entry) => {
                        this.node.entry = entry
                        // Draft nodes should immidiatly go to edit mode
                        this.edit = entry.is_draft
                    })
                    .finally(() => { this.requestInFlight = false })
            }
        },
        clearDraft () {
            if (this.node && this.node.entry) {
                this.newEntryContent = { ...this.node.entry.content }
                this.title = this.node.entry.title
            } else {
                this.newEntryContent = Object()
                this.title = ''
            }
            // Draft nodes should NOT immidiatly go to edit mode, only after saving it should stay in edit mode
            this.edit = false
        },
        deleteEntry (isDraft = false) {
            if (isDraft) {
                if (window.confirm('Are you sure that you want to discard this entry?')) {
                    this.requestInFlight = true
                    entryAPI.delete(this.node.entry.id, { customSuccessToast: 'Entry successfully discarded.' })
                        .then((data) => {
                            this.clearDraft()
                            this.$emit('entry-deleted', data)
                        })
                        .finally(() => { this.requestInFlight = false })
                }
            } else if (window.confirm('Are you sure that you want to delete this entry?')) {
                this.requestInFlight = true
                entryAPI.delete(this.node.entry.id, { customSuccessToast: 'Entry successfully deleted.' })
                    .then((data) => {
                        this.clearDraft()
                        this.$emit('entry-deleted', data)
                    })
                    .finally(() => { this.requestInFlight = false })
            }
        },
        createEntry (isDraft = false) {
            if (isDraft || this.checkRequiredFields()) {
                this.requestInFlight = true

                // Strip the categories from the request to be sent.
                const { categories, ...newEntryContentWithoutCategories } = this.newEntryContent
                // Instead, only the ids of the categories are used.
                let categoryIds = []
                if (this.newEntryContent.categories) {
                    categoryIds = this.newEntryContent.categories.map((category) => category.id)
                }

                entryAPI.create({
                    journal_id: this.$route.params.jID,
                    template_id: this.template.id,
                    content: newEntryContentWithoutCategories,
                    node_id: this.node && this.node.id > 0 ? this.node.id : null,
                    category_ids: categoryIds,
                    title: this.template.allow_custom_title ? this.title : null,
                    is_draft: isDraft,
                }, { customSuccessToast: 'Entry successfully posted.' })
                    .then((data) => {
                        this.$emit('entry-posted', data)
                    })
                    .finally(() => { this.requestInFlight = false })
            }
        },
        checkRequiredFields () {
            if (this.template.field_set.some((field) => field.required && !this.newEntryContent[field.id])) {
                this.$toasted.error('Some required fields are empty.')
                return false
            }

            return true
        },
        entryContentHasPendingChanges () {
            // For newly created entries simply check if any field or the title has any content
            if (this.create) {
                return this.template.field_set.some((field) => this.newEntryContent[field.id])
                    || this.title !== this.node.entry.title
            } else {
                // For existing entries check if the content or title is changed
                return !this.$_isEqual(this.newEntryContent, this.node.entry.content)
                    || this.title !== this.node.entry.title
            }
        },
        safeToLeave () {
            // It is safe to leave the entry if no entry is selected, or the selected entry has no pending changes
            return !this.node || !this.node.entry || !this.entryContentHasPendingChanges()
        },
    },
}
</script>
