<!--
    Loads in an entry for a student, which was previously filled in
    by the student using an Add-Node or an empty Deadline-Entry-Node.
    It will also show the grade once it's published by responsible user
    and give a possibility to edit an entry if it still has the
    needed privileges.
 -->
<template>
    <div>
        <!-- Edit mode. -->
        <b-card
            v-if="saveEditMode == 'Save'"
            class="no-hover"
            :class="$root.getBorderClass(cID)"
        >
            <div
                v-if="gradePublished"
                class="ml-2 btn float-right multi-form theme-shadow no-hover"
            >
                {{ entryNode.entry.grade.grade }}
            </div>

            <h2 class="theme-h2 mb-2">
                {{ entryNode.entry.template.name }}
            </h2>
            <sandboxed-iframe
                v-if="entryNode.description"
                :content="entryNode.description"
            />
            <entry-fields
                :template="entryNode.entry.template"
                :completeContent="completeContent"
                :displayMode="false"
                :nodeID="entryNode.nID"
                :entryID="entryNode.entry.id"
                @uploadingFile="uploadingFiles ++"
                @finishedUploadingFile="uploadingFiles --"
            />

            <b-alert
                :show="dismissCountDown"
                dismissible
                variant="secondary"
                @dismissed="dismissCountDown=0"
            >
                Some fields are empty or incorrectly formatted.
            </b-alert>
            <b-button
                class="add-button float-right mt-2"
                :class="{'input-disabled': uploadingFiles > 0}"
                @click="saveEdit"
            >
                <icon name="save"/>
                Save
            </b-button>
            <b-button
                class="delete-button mt-2"
                @click="cancel"
            >
                <icon name="ban"/>
                Cancel
            </b-button>
        </b-card>
        <!-- Overview mode. -->
        <b-card
            v-else
            class="no-hover"
            :class="$root.getBorderClass(cID)"
        >
            <div
                v-if="gradePublished"
                class="ml-2 grade-section grade"
            >
                {{ entryNode.entry.grade.grade }}
            </div>
            <div
                v-else-if="!entryNode.entry.editable"
                class="ml-2 grade-section grade"
            >
                <icon name="hourglass-half"/>
            </div>
            <div v-else>
                <b-button
                    v-if="entryNode.entry.editable"
                    class="ml-2 delete-button float-right multi-form"
                    @click="deleteEntry"
                >
                    <icon name="trash"/>
                    Delete
                </b-button>
                <b-button
                    v-if="entryNode.entry.editable"
                    class="ml-2 change-button float-right multi-form"
                    @click="saveEdit"
                >
                    <icon name="edit"/>
                    Edit
                </b-button>
            </div>

            <h2 class="theme-h2 mb-2">
                {{ entryNode.entry.template.name }}
            </h2>
            <entry-fields
                :nodeID="entryNode.nID"
                :template="entryNode.entry.template"
                :completeContent="completeContent"
                :displayMode="true"
                :journalID="journal.id"
                :entryID="entryNode.entry.id"
            />
            <hr class="full-width"/>
            <div>
                <span class="timestamp">
                    <span v-if="entryNode.entry.last_edited_by == null">
                        Submitted on: {{ $root.beautifyDate(entryNode.entry.creation_date) }}
                        <template v-if="assignment && assignment.is_group_assignment">
                            by {{ entryNode.entry.author }}
                        </template>
                    </span>
                    <span v-else>
                        Last edited: {{ $root.beautifyDate(entryNode.entry.last_edited) }}
                        <template v-if="assignment && assignment.is_group_assignment">
                            by {{ entryNode.entry.last_edited_by }}
                        </template>
                    </span>
                    <b-badge
                        v-if="entryNode.due_date
                            && new Date(entryNode.due_date) < new Date(entryNode.entry.last_edited)"
                        class="late-submission-badge"
                    >
                        LATE
                    </b-badge><br/>
                </span>
            </div>
        </b-card>

        <comments
            :eID="entryNode.entry.id"
            :entryGradePublished="gradePublished"
        />
    </div>
</template>

<script>
import sandboxedIframe from '@/components/assets/SandboxedIframe.vue'
import comments from '@/components/entry/Comments.vue'
import entryFields from '@/components/entry/EntryFields.vue'

export default {
    components: {
        comments,
        entryFields,
        sandboxedIframe,
    },
    props: ['entryNode', 'cID', 'journal', 'assignment'],
    data () {
        return {
            saveEditMode: 'Edit',
            tempNode: this.entryNode,
            matchEntry: 0,
            completeContent: [],

            dismissSecs: 3,
            dismissCountDown: 0,
            showDismissibleAlert: false,
            uploadingFiles: 0,
        }
    },
    computed: {
        gradePublished () {
            return this.entryNode.entry && this.entryNode.entry.grade && this.entryNode.entry.grade.published
        },
    },
    watch: {
        entryNode () {
            this.completeContent = []
            this.tempNode = this.entryNode
            this.saveEditMode = 'Edit'
            this.setContent()
        },
    },
    created () {
        this.setContent()
    },
    methods: {
        saveEdit () {
            if (this.saveEditMode === 'Save') {
                if (this.checkFilled()) {
                    this.saveEditMode = 'Edit'
                    this.tempNode.entry.content = this.completeContent
                    this.$emit('edit-node', this.tempNode)
                } else {
                    this.dismissCountDown = this.dismissSecs
                }
            } else {
                this.saveEditMode = 'Save'
                this.completeContent = []
                this.setContent()
            }
        },
        deleteEntry () {
            if (window.confirm('Are you sure that you want to delete this entry?')) {
                this.$emit('delete-node', this.tempNode)
            }
        },
        cancel () {
            this.saveEditMode = 'Edit'
            this.completeContent = []
            this.setContent()
        },
        setContent () {
            let matchFound
            /* Loads in the data of an entry in the right order by matching
             * the different data-fields with the corresponding template-IDs. */
            this.entryNode.entry.template.field_set.sort((a, b) => a.location - b.location).forEach((templateField) => {
                matchFound = false

                matchFound = this.entryNode.entry.content.some((content) => {
                    if (content.field === templateField.id) {
                        this.completeContent.push({
                            data: content.data,
                            id: content.field,
                            contentID: content.id,
                        })

                        return true
                    }
                    return false
                })

                if (!matchFound) {
                    this.completeContent.push({
                        data: null,
                        id: templateField.id,
                    })
                }
            })
        },
        checkFilled () {
            for (let i = 0; i < this.completeContent.length; i++) {
                const content = this.completeContent[i]
                const field = this.entryNode.entry.template.field_set.sort((a, b) => a.location - b.location)[i]
                if (field.required && !content.data) {
                    return false
                }
            }

            return true
        },
    },
}
</script>
