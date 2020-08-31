<template>
    <image-file-display
        v-if="type == 'img'"
        :file="file"
    />
    <file-download-button
        v-else-if="type == 'file'"
        :file="file"
    />
    <pdf-display
        v-else-if="type == 'pdf'"
        :file="file"
    />
</template>

<script>
import fileDownloadButton from '@/components/assets/file_handling/FileDownloadButton.vue'
import imageFileDisplay from '@/components/assets/file_handling/ImageFileDisplay.vue'
import pdfDisplay from '@/components/assets/PdfDisplay.vue'

export default {
    components: {
        pdfDisplay,
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
            const extension = this.file.file_name.split('.').pop()
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
