<template>
    <span>
        <div
            v-if="files.length > 0"
            class="file-list multi-form round-border p-2"
        >
            <div
                v-for="(file, i) in files"
                :key="i"
            >
                <file-display :file="file">
                    <icon
                        v-if="attachNew"
                        name="trash"
                        class="ml-2 float-right mt-1 trash-icon"
                        @click.native.stop="$emit('fileRemoved', i)"
                    />
                </file-display>
            </div>
        </div>
        <b-button
            v-if="attachNew"
            class="btn change-button mr-2"
            @click="$refs['file-upload'].openFileUpload()"
        >
            <icon name="paperclip"/>
            Attach file
            <file-upload-input
                ref="file-upload"
                :acceptedFiletype="'*/*'"
                :maxSizeBytes="$root.maxFileSizeBytes"
                :autoUpload="true"
                :plain="true"
                hidden
                @uploading-file="(file) => $emit('uploading-file', file)"
                @fileUploadSuccess="(file) => $emit('fileUploadSuccess', file)"
                @fileUploadFailed="(file) => $emit('fileUploadFailed', file)"
            />
        </b-button>
    </span>
</template>
<script>
import fileDisplay from '@/components/assets/file_handling/FileDisplay.vue'
import fileUploadInput from '@/components/assets/file_handling/FileUploadInput.vue'

export default {
    components: {
        fileUploadInput,
        fileDisplay,
    },
    props: {
        files: {
            required: true,
        },
        attachNew: {
            default: false,
        },
    },
}
</script>
<style lang="sass">
.file-list
    border: 2px solid $theme-dark-grey
    font-weight: bold
</style>
