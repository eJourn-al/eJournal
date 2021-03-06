<template>
    <div class="pdf-display">
        <div
            class="controls unselectable"
            @click="handleDownload"
        >
            <icon
                name="file"
                class="shift-up-2 fill-blue"
            />
            <b class="ml-1">
                {{ file.file_name }}
            </b>
            <slot/>
        </div>
        <template v-if="show">
            <div
                v-if="loadedRatio > 0 && loadedRatio < 1"
                :style="{ width: loadedRatio * 100 + '%' }"
                style="background-color: green; color: white; text-align: center"
                class="round-border"
            >
                {{ Math.floor(loadedRatio * 100) }}%
            </div>
            <div
                v-if="loaded && numPages !== 0"
                class="pdf-controls"
            >
                <icon
                    name="undo"
                    @click.native="rotate -= 90"
                />
                <icon
                    name="undo"
                    class="redo mr-4"
                    @click.native="rotate += 90"
                />
                <icon
                    name="angle-left"
                    class="mr-2"
                    @click.native="page = (page - 1 > 0) ? page - 1 : numPages"
                />
                <b-input
                    v-model="displayPageNumber"
                    :max="numPages"
                    type="number"
                    min="1"
                    class="inline"
                    @input="validatePageInput"
                />
                / {{ numPages }}
                <icon
                    name="angle-right"
                    class="mr-4 ml-1"
                    @click.native="page = (page + 1 > numPages) ? 1 : page + 1"
                />
                <icon
                    name="print"
                    @click.native="print"
                />
                <icon
                    name="save"
                    class="mr-4"
                    @click.native="downloadLink.click()"
                />
            </div>
            <pdf
                v-if="fileURL"
                :ref="'pdf'"
                :src="fileURL"
                :page="page"
                :rotate="rotate"
                class="pdf-viewer d-block"
                @password="password"
                @progress="loadedRatio = $event"
                @error="error"
                @num-pages="numPages = $event"
                @link-clicked="page = $event"
                @loaded="loaded = true"
            />
        </template>
    </div>
</template>

<script>
import auth from '@/api/auth.js'
import pdf from 'vue-pdf'
import sanitization from '@/utils/sanitization.js'

export default {
    components: {
        pdf,
    },
    props: {
        file: {
            required: true,
        },
        display: {
            default: false,
        },
    },
    data () {
        return {
            show: false,
            fileURL: null,
            loadedRatio: 0,
            page: 1,
            displayPageNumber: 1,
            numPages: 0,
            rotate: 0,
            loaded: false,
            downloadLink: null,
        }
    },
    watch: {
        page (val) { this.displayPageNumber = val },
    },
    created () {
        this.show = this.display

        if (this.show) { this.fileDownload() }
    },
    methods: {
        handleDownload () {
            this.show = !this.show

            if (!this.fileURL && this.show) {
                this.fileDownload()
            }
        },
        /* Ensures the input is within range of the PDF pages. */
        validatePageInput (input) {
            const parsed = parseInt(input.data, 10)

            if (parsed < 1) {
                this.page = 1
            } else if (parsed > this.numPages) {
                this.page = this.numPages
            } else if (!Number.isNaN(parsed)) {
                this.page = parseInt(input.data, 10)
            }
        },
        password () {
            this.$toasted.error('Password handling is not implemented.')
        },
        error (err) {
            this.$toasted.error(sanitization.escapeHtml(err))
        },
        print () {
            this.$refs.pdf.print()
        },
        fileDownload () {
            auth.downloadFile(this.file.download_url)
                .then((response) => {
                    try {
                        const blob = new Blob([response.data], { type: response.headers['content-type'] })
                        this.fileURL = window.URL.createObjectURL(blob)

                        this.downloadLink = document.createElement('a')
                        this.downloadLink.href = this.fileURL
                        this.downloadLink.download = this.file.file_name
                        document.body.appendChild(this.downloadLink)
                    } catch (_) {
                        this.$toasted.error('Error creating file.')
                    }
                })
        },
    },
    destroy () { this.downloadLink.remove() },
}
</script>

<style lang="sass">
.pdf-display
    .pdf-controls
        z-index: 1
        padding: 10px
        width: 100%
        position: absolute
        text-align: center
        margin-bottom: 10px
        justify-content: center
        transition: opacity 0.3s cubic-bezier(.25,.8,.25,1) !important
        opacity: 0.2
        &:hover
            opacity: 1
        svg
            width: 1.6em
            height: 1.6em
            border-radius: 5px
            border: 1px solid $border-color
            padding: 5px
            background-color: white
            &:hover
                background-color: $theme-light-grey
                cursor: pointer

    .redo
        -moz-transform: scale(-1, 1)
        -webkit-transform: scale(-1, 1)
        -o-transform: scale(-1, 1)
        -ms-transform: scale(-1, 1)
        transform: scale(-1, 1)
</style>
