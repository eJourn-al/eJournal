<template>
    <div>
        <b-form-file
            ref="bonusInput"
            accept="*/*.csv"
            :state="Boolean(file)"
            :placeholder="placeholderText"
            class="fileinput mb-2"
            @change="fileHandler"
        />
        <b-button
            v-if="!autoUpload"
            class="add-button float-right"
            :class="{ 'input-disabled': !file }"
            @click="uploadFile"
        >
            <icon name="upload"/>
            Upload
        </b-button>

        <div v-if="errorLogs">
            <b class="text-red">Errors in file:</b>
            <div
                v-if="errorLogs.non_participants || errorLogs.unknown_users"
                class="text-dark-grey mb-1"
            >
                <i>Note: it is likely that one or more of the users reported as unknown or non participant still need
                    to visit this assignment on the LMS (Canvas).</i>
            </div>
            <b
                v-if="errorLogs.general"
                class="mb-1"
            >
                {{ errorLogs.general }}
            </b>
            <div
                v-if="errorLogs.unknown_users"
                class="mb-1"
            >
                <b>The following users do not exist:</b><br/>
                <span
                    v-for="(username, lineNumber) in errorLogs.unknown_users"
                    :key="`unknown-users-${lineNumber}-${username}`"
                >
                    <b>&emsp;&emsp;&emsp;{{ lineNumber }})</b> {{ username }}<br/>
                </span>
            </div>
            <div
                v-if="errorLogs.non_participants"
                class="mb-1"
            >
                <b>The following users are not participants of the assignment:</b><br/>
                <span
                    v-for="(username, lineNumber) in errorLogs.non_participants"
                    :key="`non_participants-${lineNumber}-${username}`"
                >
                    <b>&emsp;&emsp;&emsp;{{ lineNumber }})</b> {{ username }}<br/>
                </span>
            </div>
            <div
                v-if="errorLogs.incorrect_format_lines"
                class="mb-1"
            >
                <b>The following lines are incorrectly formatted:</b><br/>
                <span
                    v-for="(content, lineNumber) in errorLogs.incorrect_format_lines"
                    :key="`incorrect-format-${lineNumber}-${content}`"
                >
                    <b>&emsp;&emsp;&emsp;{{ lineNumber }})</b> {{ content }}<br/>
                </span>
            </div>
            <div v-if="errorLogs.duplicates">
                <b>The following users occur twice:</b><br/>
                <span
                    v-for="(username, lineNumber) in errorLogs.duplicates"
                    :key="`duplicates-${lineNumber}-${username}`"
                >
                    <b>&emsp;&emsp;&emsp;{{ lineNumber }})</b> {{ username }}<br/>
                </span>
            </div>
        </div>
    </div>
</template>

<script>
import auth from '@/api/auth.js'

export default {
    props: {
        aID: {
            required: true,
            String,
        },
        autoUpload: {
            default: false,
            Boolean,
        },
        endpoint: {
            default: 'users/upload',
        },
        placeholder: {
            default: 'No file chosen',
        },
        contentID: {
            default: null,
        },
    },
    data () {
        return {
            placeholderText: 'No file chosen',
            file: null,
            errorLogs: null,
        }
    },
    created () {
        // Assume the given file is present in the backend
        if (this.placeholder !== null && this.placeholder !== 'No file chosen') {
            this.file = true
            this.placeholderText = this.placeholder
        }
    },
    methods: {
        fileHandler (e) {
            const files = e.target.files

            if (!files.length) { return }
            if (files[0].size > this.$root.maxFileSizeBytes) {
                this.$toasted.error(
                    `The selected file exceeds the maximum file size of: ${this.$root.maxFileSizeBytes} bytes.`)
                return
            }

            this.file = files[0]
            this.resetErrorLogs()

            this.$emit('fileSelect', this.file.name)

            if (this.autoUpload) { this.uploadFile() }
        },
        uploadFile () {
            const formData = new FormData()
            formData.append('file', this.file)
            formData.append('assignment_id', this.aID)
            formData.append('content_id', this.contentID)

            auth.uploadFile(this.endpoint, formData, {
                customSuccessToast: 'Successfully imported bonus points.',
                customErrorToast: 'Something is wrong with the uploaded file.',
            })
                .then(() => {
                    this.$emit('bonusPointsSuccessfullyUpdated', this.file.name)
                    this.file = null
                    this.$refs.bonusInput.reset()
                })
                .catch((error) => {
                    this.$emit('bonusPointsFileFormatIssues', this.file.name)
                    this.file = null
                    this.$refs.bonusInput.reset()
                    this.errorLogs = error.response.data.description
                })
        },
        resetErrorLogs () {
            this.errorLogs = null
        },
    },
}
</script>
