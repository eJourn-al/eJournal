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
            </template>

            <entry-title
                :template="template"
                :node="node"
            >
                <b-button
                    v-if="!create && node.entry.editable"
                    class="ml-auto"
                    :class="(edit) ? 'red-button' : 'orange-button'"
                    @click="edit = !edit"
                >
                    <icon :name="(edit) ? 'ban' : 'edit'"/>
                    {{ (edit) ? 'Cancel' : 'Edit' }}
                </b-button>
            </entry-title>

            <sandboxed-iframe
                v-if="node && node.description && (edit || create)"
                :content="node.description"
            />
            <files-list
                v-if="node && (edit || create)"
                :files="node.attached_files"
            />
            <entry-fields
                :template="template"
                :content="newEntryContent"
                :edit="edit || create"
                :nodeID="node ? node.nID : -1"
                @uploading-file="uploadingFiles ++"
                @finished-uploading-file="uploadingFiles --"
            />

            <entry-categories
                :id="`entry-${(create) ? Math.random() : node.entry.id}-categories`"
                :create="create"
                :edit="edit"
                :entry="(create) ? newEntryContent : node.entry"
                :template="template"
            />

            <template v-if="edit">
                <hr/>

                <b-row
                    no-gutters
                    class="mt-2"
                >
                    <b-button
                        class="red-button"
                        @click="deleteEntry"
                    >
                        <icon name="trash"/>
                        Delete
                    </b-button>

                    <b-button
                        class="green-button ml-auto"
                        :class="{ 'input-disabled': requestInFlight || uploadingFiles > 0 }"
                        @click="saveChanges"
                    >
                        <icon name="save"/>
                        Save
                    </b-button>
                </b-row>
            </template>

            <b-button
                v-else-if="create"
                class="green-button float-right"
                :class="{ 'input-disabled': requestInFlight || uploadingFiles > 0 }"
                @click="createEntry"
            >
                <icon name="paper-plane"/>
                Post
            </b-button>

            <template v-else>
                <hr class="full-width"/>

                <div class="full-width timestamp">
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
                        pill
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
                            ${node.entry.jir.processor.full_name}`"
                        pill
                        class="imported-entry-badge"
                    >
                        IMPORTED
                    </b-badge>
                </div>
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
import EntryCategories from '@/components/category/EntryCategories.vue'
import EntryFields from '@/components/entry/EntryFields.vue'
import EntryTitle from '@/components/entry/EntryTitle.vue'
import SandboxedIframe from '@/components/assets/SandboxedIframe.vue'
import filesList from '@/components/assets/file_handling/FilesList.vue'

import entryAPI from '@/api/entry.js'

export default {
    components: {
        EntryFields,
        EntryTitle,
        SandboxedIframe,
        Comments,
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

                const categoryIds = this.newEntryContent.categories.map(category => category.id)
                delete this.newEntryContent.categories

                entryAPI.create({
                    journal_id: this.$route.params.jID,
                    template_id: this.template.id,
                    content: this.newEntryContent,
                    node_id: this.node && this.node.nID > 0 ? this.node.nID : null,
                    category_ids: categoryIds,
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
