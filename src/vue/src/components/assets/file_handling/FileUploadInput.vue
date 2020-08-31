<template>
    <div>
        <b-form-file
            ref="formFile"
            :accept="acceptedFiletype"
            :state="Boolean(file)"
            :placeholder="placeholderText"
            :plain="plain"
            class="fileinput"
            @change="fileHandler"
        />
        <small
            v-if="acceptedFiletype !== '*/*'"
            class="multi-form"
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
        }
    },
    created () {
        // Assume the given file is present in the backend
        if (this.placeholder !== null && this.placeholder !== 'No file chosen') {
            this.file = true
        }
        this.placeholderText = this.placeholder ? this.placeholder : 'No file chosen'
    },
    methods: {
        fileHandler (e) {
            const files = e.target.files

            if (!files.length) { return }
            if (files[0].size > this.maxSizeBytes) {
                this.$toasted.error(`The selected file exceeds the maximum file size of: ${this.maxSizeBytes} bytes.`)
                return
            }

            this.file = files[0]

            this.$emit('fileSelect', this.file.file_name)

            if (this.autoUpload) { this.uploadFile() }
        },
        uploadFile () {
            const formData = new FormData()
            formData.append('file', this.file)
            this.$emit('uploading-file')
            auth.uploadFile(this.endpoint, formData, { customSuccessToast: 'File upload success.' })
                .then((resp) => {
                    this.$emit('fileUploadSuccess', resp.data)
                })
                .catch(() => {
                    this.$emit('fileUploadFailed', this.file.file_name)
                    this.file = null
                })
        },
        openFileUpload () {
            this.$refs.formFile.$el.click()
        },
    },
}
</script>
