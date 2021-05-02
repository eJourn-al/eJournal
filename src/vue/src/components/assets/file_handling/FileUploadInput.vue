<template>
    <div>
        <b-form-file
            ref="formFile"
            v-model="file"
            :accept="acceptedFiletype"
            :state="state"
            :placeholder="placeholderText"
            :plain="plain"
            class="fileinput"
            @change="fileHandler"
        />
        <b-progress
            v-if="uploading"
            class="mt-2"
        >
            <b-progress-bar
                :value="loaded"
                :max="total"
                :label="progressLabel"
                show-progress
                animated
            />
        </b-progress>

        <small
            v-if="acceptedFiletype !== '*/*'"
            class="mb-2"
        >
            <b>Accepted extension(s):</b> {{ acceptedFiletype }}
        </small>
    </div>
</template>

<script>
import auth from '@/api/auth.js'

export default {
    props: {
        acceptedFiletype: {
            required: true,
            String,
        },
        maxSizeBytes: {
            required: true,
            Number,
        },
        aID: {
            default: null,
            String,
        },
        autoUpload: {
            default: false,
            Boolean,
        },
        endpoint: {
            default: 'files',
        },
        placeholder: {
            default: 'No file chosen',
        },
        plain: {
            default: false,
        },
        contentID: {
            default: null,
        },
    },
    data () {
        return {
            placeholderText: 'No file chosen',
            file: null,
            state: null,
            loaded: 0,
            total: 100,
            uploading: false,
        }
    },
    computed: {
        progressLabel () {
            if (this.loaded === this.total) {
                return 'Processing...'
            }
            return `${Math.floor((this.loaded / this.total) * 100)}%`
        },
    },
    created () {
        // Assume the given file is present in the backend, create a dummy file
        if (this.placeholder !== null && this.placeholder !== 'No file chosen') {
            const blob = new Blob([''], { type: 'text/html' })
            blob.lastModifiedDate = new Date()
            blob.name = 'dummy_file'
            this.file = new File([blob], blob.name)
        }
        this.placeholderText = this.placeholder ? this.placeholder : 'No file chosen'
    },
    methods: {
        fileHandler (e) {
            const files = e.target.files

            if (!files || !files.length) { return }

            const file = files[0]

            if (file.size > this.maxSizeBytes) {
                this.$toasted.error(
                    `The selected file exceeds the maximum file size of ${this.$root.maxFileSizeLabel}.`)
                this.state = false
            } else if (file.name.length > this.$root.maxFileNameLength) {
                this.$toasted.error(
                    `The selected file exceeds the maximum file name length of ${this.$root.maxFileNameLength}.`)
                this.state = false
            } else {
                this.file = file

                this.$emit('fileSelect', this.file.file_name)

                if (this.autoUpload) { this.uploadFile() }
            }
        },
        resetUploadState () {
            this.uploading = false
            this.total = 100
            this.progress = 0
        },
        uploadFile () {
            const formData = new FormData()
            formData.append('file', this.file)

            this.uploading = true
            this.$emit('uploading-file')
            auth.uploadFile(
                this.endpoint,
                formData,
                {
                    onUploadProgress: (e) => {
                        this.loaded = e.loaded
                        this.total = e.total
                    },
                },
                { customSuccessToast: 'File upload success.' },
            )
                .then((resp) => {
                    this.$emit('fileUploadSuccess', resp.data.file)
                    this.state = true
                })
                .catch(() => {
                    this.$emit('fileUploadFailed', this.file.file_name)
                    this.file = null
                    this.state = false
                })
                .finally(() => {
                    this.resetUploadState()
                })
        },
        openFileUpload () {
            this.$refs.formFile.$el.click()
        },
    },
}
</script>
