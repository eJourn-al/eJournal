<template>
    <div>
        <b-card
            class="no-hover"
            :class="$root.getBorderClass($route.params.cID)"
        >
            <template v-if="!(edit || create)">
                <div
                    v-if="gradePublished"
                    class="ml-2 grade-section grade"
                >
                    {{ node.entry.grade.grade }}
                </div>
                <div
                    v-else-if="!node.entry.editable"
                    class="ml-2 grade-section grade"
                >
                    <icon name="hourglass-half"/>
                </div>
                <div v-else-if="node.entry.editable">
                    <b-button
                        class="ml-2 delete-button float-right multi-form"
                        @click="deleteEntry"
                    >
                        <icon name="trash"/>
                        Delete
                    </b-button>
                    <b-button
                        class="ml-2 change-button float-right multi-form"
                        @click="edit = true"
                    >
                        <icon name="edit"/>
                        Edit
                    </b-button>
                </div>
            </template>

            <h2 class="theme-h2 mb-2">
                {{ template.name }}
            </h2>
            <sandboxed-iframe
                v-if="node && node.description && (edit || create)"
                :content="node.description"
            />
            <files-list
                v-if="node && node.description && (edit || create)"
                :files="node.files"
            />
            <entry-fields
                :template="template"
                :content="newEntryContent"
                :edit="edit || create"
                :nodeID="node ? node.nID : -1"
                @uploading-file="uploadingFiles ++"
                @finished-uploading-file="uploadingFiles --"
            />

            <template v-if="edit">
                <b-button
                    class="add-button float-right mt-2"
                    :class="{ 'input-disabled': requestInFlight || uploadingFiles > 0 }"
                    @click="saveChanges"
                >
                    <icon name="save"/>
                    Save
                </b-button>
                <b-button
                    class="delete-button mt-2"
                    @click="edit = false"
                >
                    <icon name="ban"/>
                    Cancel
                </b-button>
            </template>
            <b-button
                v-else-if="create"
                class="add-button float-right"
                :class="{ 'input-disabled': requestInFlight || uploadingFiles > 0 }"
                @click="createEntry"
            >
                <icon name="paper-plane"/>
                Post
            </b-button>
            <div
                v-else
                class="full-width timestamp"
            >
                <hr class="full-width"/>
                <template
                    v-if="(new Date(node.entry.last_edited).getTime() - new Date(node.entry.creation_date)
                        .getTime()) / 1000 < 3"
                >
                    Submitted:
                </template>
                <template v-else>
                    Last edited:
                </template>
                {{ $root.beautifyDate(node.entry.last_edited) }} by {{ node.entry.last_edited_by }}
                <b-badge
                    v-if="node.due_date
                        && new Date(node.due_date) < new Date(node.entry.last_edited)"
                    v-b-tooltip:hover="'This entry was submitted after the due date'"
                    class="late-submission-badge"
                >
                    LATE
                </b-badge>
                <b-badge
                    v-if="node.entry.jir"
                    v-b-tooltip:hover="
                        `This entry has been imported from the assignment
                        ${node.entry.jir.source.assignment.name}
                        (${node.entry.jir.source.assignment.course.abbreviation}), approved by
                        ${node.entry.jir.processor.full_name}`
                    "
                    class="imported-entry-badge"
                >
                    IMPORTED
                </b-badge>
            </div>
        </b-card>
        <comments
            v-if="node && node.entry"
            :eID="node.entry.id"
        />
    </div>
</template>

<script>
import SandboxedIframe from '@/components/assets/SandboxedIframe.vue'
import EntryFields from '@/components/entry/EntryFields.vue'
import Comments from '@/components/entry/Comments.vue'
import filesList from '@/components/assets/file_handling/FilesList.vue'

import entryAPI from '@/api/entry.js'

export default {
    components: {
        EntryFields,
        SandboxedIframe,
        Comments,
        filesList,
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
    },
    data () {
        return {
            edit: false,
            requestInFlight: false,
            newEntryContent: () => Object(),
            uploadingFiles: 0,
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
                if (this.node && this.node.entry) {
                    this.newEntryContent = Object.assign({}, this.node.entry.content)
                } else {
                    this.newEntryContent = Object()
                }
                this.edit = false
            },
        },
    },
    methods: {
        saveChanges () {
            if (this.checkRequiredFields()) {
                this.requestInFlight = true
                entryAPI.update(this.node.entry.id, { content: this.newEntryContent },
                    { customSuccessToast: 'Entry successfully updated.' })
                    .then((entry) => {
                        this.node.entry = entry
                        this.edit = false
                        this.requestInFlight = false
                    })
                    .catch(() => {
                        this.requestInFlight = false
                    })
            }
        },
        deleteEntry () {
            if (window.confirm('Are you sure that you want to delete this entry?')) {
                this.requestInFlight = true
                entryAPI.delete(this.node.entry.id, { customSuccessToast: 'Entry successfully deleted.' })
                    .then((data) => {
                        this.requestInFlight = false
                        this.$emit('entry-deleted', data)
                    })
                    .catch(() => { this.requestInFlight = false })
            }
        },
        createEntry () {
            if (this.checkRequiredFields()) {
                this.requestInFlight = true
                entryAPI.create({
                    journal_id: this.$route.params.jID,
                    template_id: this.template.id,
                    content: this.newEntryContent,
                    node_id: this.node && this.node.nID > 0 ? this.node.nID : null,
                }, { customSuccessToast: 'Entry successfully posted.' })
                    .then((data) => {
                        this.requestInFlight = false
                        this.$emit('entry-posted', data)
                    })
                    .catch(() => { this.requestInFlight = false })
            }
        },
        checkRequiredFields () {
            if (this.template.field_set.some(field => field.required && !this.newEntryContent[field.id])) {
                this.$toasted.error('Some required fields are empty.')
                return false
            }

            return true
        },
        safeToLeave () {
            // It is safe to leave the entry if it is not currently being edited AND if no content for an entry to be
            // created is provided.
            return !this.edit && !(this.create && this.template.field_set.some(field => this.newEntryContent[field.id]))
        },
    },
}
</script>
