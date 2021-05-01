<template>
    <div class="image-display round-border">
        <div
            class="controls unselectable"
            @click="handleDownload"
        >
            <icon
                name="image"
                class="shift-up-2 fill-blue"
            />
            <b class="ml-1">
                {{ file.file_name }}
            </b>
            <slot/>
        </div>
        <img
            v-if="fileURL && show"
            class="full-width round-border"
            :class="showImage"
            :src="fileURL"
        />
    </div>
</template>

<script>
import auth from '@/api/auth.js'

export default {
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
        }
    },
    computed: {
        showImage () {
            return this.show ? 'open' : 'closed'
        },
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
        fileDownload () {
            auth.downloadFile(this.file.download_url)
                .then((response) => {
                    try {
                        const blob = new Blob([response.data], { type: response.headers['content-type'] })
                        this.fileURL = window.URL.createObjectURL(blob)
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
.image-display
    img
        display: inline
</style>
