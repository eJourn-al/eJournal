<template>
    <div
        class="comment-card"
    >
        <img
            :src="comment.author.profile_picture"
            class="theme-img profile-picture-sm no-hover"
        />
        <b-card
            :class="$root.getBorderClass($route.params.cID)"
            class="no-hover"
        >
            <!-- Show comment -->
            <div v-if="!editing && !createCard">
                <sandboxed-iframe
                    v-if="comment.text"
                    :content="comment.text"
                />
                <files-list :files="comment.files"/>
                <hr/>
                <b>{{ comment.author.full_name }}</b>
                <icon
                    v-if="comment.can_edit"
                    name="trash"
                    class="float-right trash-icon"
                    @click.native="$emit('deleteComment', comment.id)"
                />
                <icon
                    v-if="comment.can_edit"
                    name="edit"
                    scale="1.07"
                    class="float-right ml-2 edit-icon"
                    @click.native="editing = true"
                />
                <span
                    v-if="comment.published && !comment.last_edited"
                    class="timestamp"
                >
                    {{ $root.beautifyDate(comment.creation_date) }}<br/>
                </span>
                <span
                    v-else-if="comment.published"
                    v-b-tooltip:hover="`Last edit by: ${comment.last_edited_by}`"
                    class="timestamp"
                >
                    Last edited: {{ $root.beautifyDate(comment.last_edited) }}
                </span>
                <span
                    v-else
                    class="timestamp"
                >
                    <icon
                        name="hourglass-half"
                        scale="0.8"
                    />
                    Will be published along with grade<br/>
                </span>
            </div>
            <!-- Edit comment -->
            <div v-else>
                <text-editor
                    :id="textEditorKey"
                    :key="textEditorKey"
                    :ref="textEditorKey"
                    v-model="comment.text"
                    :basic="true"
                    :footer="false"
                    class="multi-form"
                    @startedUploading="uploadingFiles ++"
                    @finishedUploading="uploadingFiles --"
                />
                <files-list
                    :attachNew="true"
                    :files="comment.files"
                    @uploading-file="uploadingFiles ++"
                    @fileUploadSuccess="comment.files.push($event) && uploadingFiles --"
                    @fileUploadFailed="uploadingFiles --"
                    @fileRemoved="(i) => comment.files.splice(i, 1)"
                />
                <template v-if="createCard">
                    <dropdown-button
                        v-if="$hasPermission('can_grade')"
                        :up="true"
                        :selectedOption="$store.getters['preferences/saved'].comment_button_setting"
                        :options="{
                            p: {
                                text: 'Send',
                                icon: 'paper-plane',
                                class: '',
                            },
                            s: {
                                text: 'Send & publish after grade',
                                icon: 'paper-plane',
                                class: '',
                            },
                            g: {
                                text: 'Send & publish grade',
                                icon: 'paper-plane',
                                class: '',
                            },
                        }"
                        :class="disableSend"
                        class="ml-2 float-right"
                        @change-option="(e) => $emit('change-option', e)"
                        @click="createComment"
                    />
                    <b-button
                        v-else
                        :class="disableSend"
                        class="ml-2 float-right"
                        @click="createComment('p')"
                    >
                        <icon name="paper-plane"/>
                        Send
                    </b-button>
                </template>
                <template v-else>
                    <b-button
                        v-if="comment.can_edit"
                        class="red-button"
                        @click="resetComment()"
                    >
                        <icon name="ban"/>
                        Cancel
                    </b-button>
                    <b-button
                        v-if="comment.can_edit"
                        :class="disableSend"
                        class="ml-2 green-button float-right"
                        @click="editComment()"
                    >
                        <icon name="save"/>
                        Save
                    </b-button>
                </template>
            </div>
        </b-card>
    </div>
</template>

<script>
import dropdownButton from '@/components/assets/DropdownButton.vue'
import filesList from '@/components/assets/file_handling/FilesList.vue'
import sandboxedIframe from '@/components/assets/SandboxedIframe.vue'

import commentAPI from '@/api/comment.js'

export default {
    components: {
        textEditor: () => import(/* webpackChunkName: 'text-editor' */ '@/components/assets/TextEditor.vue'),
        dropdownButton,
        sandboxedIframe,
        filesList,
    },
    props: {
        passedComment: {
            required: true,
        },
        createCard: {
            default: false,
        },
        eID: {
            default: -1,
        },
    },
    data () {
        return {
            editing: false,
            saveRequestInFlight: false,
            uploadingFiles: 0,
            comment: {},
        }
    },
    computed: {
        textEditorKey () {
            return this.createCard ? `comment-text-editor-create-${this.eID}` : `comment-text-editor-${this.comment.id}`
        },
        disableSend () {
            return this.saveRequestInFlight || this.uploadingFiles > 0 ? 'input-disabled' : ''
        },
    },
    created () {
        this.resetComment()
    },
    methods: {
        createComment (option) {
            if (this.comment.text !== '' || this.comment.files.length > 0) {
                if (option === 'g') {
                    if (this.$parent.$parent.grade.grade === '') {
                        this.$toasted.error('A grade needs to be set before it can be published.')
                        return
                    }
                    this.$emit('publish-grade')
                }

                this.saveRequestInFlight = true
                commentAPI.create({
                    entry_id: this.eID,
                    text: this.comment.text,
                    files: this.comment.files.map(f => f.id),
                    published: option === 'p' || option === 'g',
                })
                    .then((comment) => {
                        this.$emit('new-comment', comment)
                        this.resetComment()
                        this.$refs[this.textEditorKey].clearContent()
                    })
                    .finally(() => { this.saveRequestInFlight = false })
            }
        },
        editComment () {
            this.saveRequestInFlight = true
            commentAPI.update(this.comment.id, {
                text: this.comment.text,
                files: this.comment.files.map(c => c.id),
                published: this.comment.published,
            })
                .then((comment) => {
                    this.editing = false
                    this.comment = comment
                })
                .finally(() => {
                    this.saveRequestInFlight = false
                })
        },
        resetComment () {
            this.comment = JSON.parse(JSON.stringify(this.passedComment))
            this.editing = false
        },
    },
}
</script>

<style lang="sass">
.comment-card
    display: flex
    .profile-picture-sm
        margin: 0px 12px
        display: inline
    .new-comment.card-body
        display: flex
        flex-wrap: wrap
    .card
        flex: 1 1 auto
        overflow: hidden
        .card-body
            padding-bottom: 5px
            .trash-icon, .edit-icon
                margin-top: 4px
                margin-left: 4px
</style>
