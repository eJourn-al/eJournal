<template>
    <div class="d-inline-block files-list">
        <div
            v-if="files && files.length > 0"
            class="p-2 background-light-grey round-border small"
        >
            <file-display
                v-for="(file, i) in files"
                :key="i"
                :file="file"
            >
                <icon
                    v-if="attachNew"
                    name="trash"
                    class="ml-2 float-right mt-1 trash-icon"
                    scale="0.8"
                    @click.native.stop="$emit('fileRemoved', i)"
                />
            </file-display>
        </div>
        <b-button
            v-if="attachNew"
            class="green-button d-block attach-button mr-2"
            variant="link"
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
    </div>
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
.files-list
    max-width: 100%
    .pdf-viewer, img // Possible file types that are displayed inline (in sub components)
        max-width: 100%
        width: $max-app-width
        margin-bottom: 8px
    .attach-button
        &:not(:first-child)
            margin-top: 8px
</style>
