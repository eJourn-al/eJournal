<template>
    <div v-if="edit">
        <div
            v-for="field in orderedFields"
            :key="`node ${nodeID}-field-${field.id}`"
            class="multi-form"
        >
            <h2
                v-if="field.title"
                :class="{ 'required': field.required }"
                class="theme-h2 field-heading"
            >
                {{ field.title }}
            </h2>
            <sandboxed-iframe
                v-if="field.description"
                :content="field.description"
            />

            <div :class="{ 'input-disabled': readOnly }">
                <b-input
                    v-if="field.type == 't'"
                    v-model="content[field.id]"
                    class="theme-input"
                    rows="1"
                />
                <reset-wrapper
                    v-if="field.type == 'd'"
                    v-model="content[field.id]"
                >
                    <flat-pickr
                        v-model="content[field.id]"
                        class="full-width"
                        :config="$root.flatPickrConfig"
                    />
                </reset-wrapper>
                <reset-wrapper
                    v-if="field.type == 'dt'"
                    v-model="content[field.id]"
                >
                    <flat-pickr
                        v-model="content[field.id]"
                        class="full-width"
                        :config="$root.flatPickrTimeConfig"
                    />
                </reset-wrapper>
                <file-upload-input
                    v-else-if="field.type == 'f'"
                    :placeholder="content[field.id] ? content[field.id].file_name : null"
                    :acceptedFiletype="field.options ? '.' + field.options.split(', ').join(', .') : '*/*'"
                    :maxSizeBytes="$root.maxFileSizeBytes"
                    :autoUpload="true"
                    :aID="$route.params.aID"
                    :contentID="content[field.id] ? content[field.id].contentID : null"
                    @uploading-file="$emit('uploading-file')"
                    @fileUploadFailed="$emit('finished-uploading-file')"
                    @fileUploadSuccess="content[field.id] = $event; $emit('finished-uploading-file')"
                />
                <b-input
                    v-else-if="field.type == 'v'"
                    v-model="content[field.id]"
                    placeholder="Enter a YouTube URL"
                    class="theme-input"
                />
                <!-- Newly added fields in template editor have id <0. -->
                <text-editor
                    v-else-if="field.type == 'rt'"
                    :id="textEditorID(field)"
                    :key="`rich-text-editor-field-${field.id > 0 ? field.id : field.location}`"
                    v-model="content[field.id]"
                    @startedUploading="$emit('uploading-file')"
                    @finishedUploading="$emit('finished-uploading-file')"
                />
                <url-input
                    v-else-if="field.type == 'u'"
                    placeholder="Enter a URL"
                    @correctUrlInput="content[field.id] = $event"
                />
                <b-form-select
                    v-else-if="field.type == 's'"
                    v-model="content[field.id]"
                    :options="parseSelectionOptions(field.options)"
                    class="theme-select"
                />
            </div>
        </div>
    </div>
    <!-- Display section -->
    <div v-else>
        <div
            v-for="field in displayFields"
            :key="`node-${nodeID}-field-${field.id}`"
            class="multi-form"
        >
            <h2
                v-if="field.title"
                :class="{ 'required': field.required }"
                class="theme-h2 field-heading"
            >
                {{ field.title }}
            </h2>
            <span
                v-if="field.type == 't'"
                class="show-enters"
            >{{ content[field.id] }}</span>
            <span
                v-else-if="field.type == 'd'"
                class="show-enters"
            >{{ $root.beautifyDate(content[field.id], true, false) }}</span>
            <span
                v-else-if="field.type == 'dt'"
                class="show-enters"
            >{{ $root.beautifyDate(content[field.id]) }}</span>
            <file-display
                v-else-if="field.type == 'f'"
                :file="content[field.id]"
            />
            <b-embed
                v-else-if="field.type == 'v'"
                :src="youtubeEmbedFromURL(content[field.id])"
                type="iframe"
                aspect="16by9"
                allowfullscreen
            />
            <sandboxed-iframe
                v-else-if="field.type == 'rt'"
                :content="content[field.id]"
            />
            <a
                v-else-if="field.type == 'u'"
                :href="content[field.id]"
            >
                {{ content[field.id] }}
            </a>
            <span v-else-if="field.type == 's'">{{ content[field.id] }}</span>
        </div>
        <i
            v-if="displayFields && displayFields.length === 0"
            class="text-grey"
        >
            This entry has no content.
        </i>
    </div>
</template>

<script>
import fileUploadInput from '@/components/assets/file_handling/FileUploadInput.vue'
import urlInput from '@/components/assets/UrlInput.vue'
import fileDisplay from '@/components/assets/file_handling/FileDisplay.vue'
import sandboxedIframe from '@/components/assets/SandboxedIframe.vue'

export default {
    components: {
        textEditor: () => import(/* webpackChunkName: 'text-editor' */ '@/components/assets/TextEditor.vue'),
        fileUploadInput,
        urlInput,
        fileDisplay,
        sandboxedIframe,
    },
    props: {
        template: {
            required: true,
        },
        content: {
            required: true,
        },
        edit: {
            type: Boolean,
            default: false,
        },
        readOnly: {
            type: Boolean,
            default: false,
        },
        nodeID: {
            default: -1,
        },
        newEntryDraftID: {
            default: -1,
        },
    },
    computed: {
        orderedFields () {
            return this.template.field_set.slice().sort((a, b) => a.location - b.location)
        },
        displayFields () {
            return this.orderedFields.filter(field => this.content[field.id])
        },
    },
    methods: {
        // from https://stackoverflow.com/a/9102270
        youtubeEmbedFromURL (url) {
            const regExp = /^.*(youtu\.be\/|v\/|u\/\w\/|embed\/|watch\?v=|&v=)([^#&?]*).*/
            const match = url.match(regExp)
            if (match && match[2].length === 11) {
                return `https://www.youtube.com/embed/${match[2]}?rel=0&amp;showinfo=0`
            } else {
                this.$toasted.error('A YouTube video field contained an invalid URL.')
                return null
            }
        },
        parseSelectionOptions (fieldOptions) {
            if (!fieldOptions) {
                return [{ value: null, text: 'Please select an option...' }]
            }
            const options = JSON.parse(fieldOptions).filter(e => e).map(x => Object({ value: x, text: x }))
            options.unshift({ value: null, text: 'Please select an option...' })
            return options
        },
        textEditorID (field) {
            return 'rich-text-editor'
                + `-assignmentID-${this.$route.params.aID}`
                + `-template-${this.template.id}`
                + `-nodeID-${this.nodeID}`
                + `-newEntryDraftID-${this.newEntryDraftID}`
                + `-field-${field.id > 0 ? `id-${field.id}` : `loc-${field.location}`}`
        },
    },
}
</script>
