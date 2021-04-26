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
                <entry-video-field-input
                    v-else-if="field.type == 'v'"
                    v-model="content[field.id]"
                    :field="field"
                />
                <!-- Newly added fields in template editor have id <0. -->
                <text-editor
                    v-else-if="field.type == 'rt'"
                    :id="`rich-text-editor-field-${field.id > 0 ? 'id-' + field.id : 'loc-' + field.location}`"
                    :key="`rich-text-editor-field-${field.id > 0 ? field.id : field.location}`"
                    v-model="content[field.id]"
                    @startedUploading="$emit('uploading-file')"
                    @finishedUploading="$emit('finished-uploading-file')"
                />
                <validated-input
                    v-else-if="field.type == 'u'"
                    v-model="content[field.id]"
                    :validator="urlValidator"
                    :validatorArgs="[false, true]"
                    placeholder="Enter a URL"
                    invalidFeedback="Enter a valid URL"
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
            <entry-video-field-display
                v-else-if="field.type == 'v'"
                :data="content[field.id]"
                :field="field"
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
import EntryVideoFieldDisplay from '@/components/entry/EntryVideoFieldDisplay.vue'
import EntryVideoFieldInput from '@/components/entry/EntryVideoFieldInput.vue'
import ValidatedInput from '@/components/assets/ValidatedInput.vue'
import fileDisplay from '@/components/assets/file_handling/FileDisplay.vue'
import fileUploadInput from '@/components/assets/file_handling/FileUploadInput.vue'
import sandboxedIframe from '@/components/assets/SandboxedIframe.vue'

import validation from '@/utils/validation.js' /* eslint-disable-line */

export default {
    components: {
        textEditor: () => import(/* webpackChunkName: 'text-editor' */ '@/components/assets/TextEditor.vue'),
        fileUploadInput,
        fileDisplay,
        sandboxedIframe,
        EntryVideoFieldDisplay,
        EntryVideoFieldInput,
        ValidatedInput,
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
    },
    data () {
        return {
            urlValidator: validation.validateURL,
        }
    },
    computed: {
        orderedFields () {
            return this.template.field_set.slice().sort((a, b) => a.location - b.location)
        },
        displayFields () {
            return this.orderedFields.filter((field) => this.content[field.id])
        },
    },
    methods: {
        parseSelectionOptions (fieldOptions) {
            if (!fieldOptions) {
                return [{ value: null, text: 'Please select an option...' }]
            }
            const options = JSON.parse(fieldOptions).filter((e) => e).map((x) => Object({ value: x, text: x }))
            options.unshift({ value: null, text: 'Please select an option...' })
            return options
        },
    },
}
</script>
