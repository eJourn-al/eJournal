<template>
    <image-file-display
        v-if="type == 'img'"
        :file="file"
    >
        <slot/>
    </image-file-display>
    <file-download-button
        v-else-if="type == 'file'"
        :file="file"
    >
        <slot/>
    </file-download-button>
    <pdf-display
        v-else-if="type == 'pdf'"
        :file="file"
    >
        <slot/>
    </pdf-display>
</template>

<script>
import fileDownloadButton from '@/components/assets/file_handling/FileDownloadButton.vue'
import imageFileDisplay from '@/components/assets/file_handling/ImageFileDisplay.vue'

export default {
    components: {
        pdfDisplay: () => import(/* webpackChunkName: 'pdf-display' */ '@/components/assets/PdfDisplay.vue'),
        fileDownloadButton,
        imageFileDisplay,
    },
    props: {
        file: {
            required: true,
        },
    },
    computed: {
        type () {
            if (!this.file) {
                return null
            }
            const extension = this.file.file_name.split('.').pop().toLowerCase()
            if (this.$root.fileTypes.img.includes(extension)) {
                return 'img'
            } else if (this.$root.fileTypes.pdf.includes(extension)) {
                return 'pdf'
            } else {
                return 'file'
            }
        },
    },
}
</script>
<style lang="sass">
.controls
    &:hover
        cursor: pointer
    b
        text-decoration: underline !important
</style>
