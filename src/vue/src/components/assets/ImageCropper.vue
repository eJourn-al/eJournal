<template>
    <div>
        <div class="profile-picture-lg profile-picture-cropper">
            <croppa
                v-model="croppa"
                :width="250"
                :height="250"
                :showRemoveButton="false"
                :showLoading="true"
                :loadingSize="50"
                :fileSizeLimit="this.$root.maxFileSizeBytes"
                :initialImage="pictureUrl"
                disableClickToChoose
                canvasColor="transparent"
                accept="image/*"
                initialSize="natural"
                initialPosition="center"
                @file-type-mismatch="onFileTypeMismatch"
                @file-size-exceed="onFileSizeExceed"
            />
        </div>
        <b-button
            class="multi-form"
            :class="{
                'mr-2': !hideSaveButton,
                'float-right': hideSaveButton,
            }"
            @click="croppa.chooseFile()"
        >
            <icon name="upload"/>
            Upload
        </b-button>
        <b-button
            class="change-button multi-form"
            @click="refreshPicture()"
        >
            <icon name="undo"/>
            Reset
        </b-button>
        <b-button
            v-if="!hideSaveButton"
            class="add-button float-right"
            @click="savePicture()"
        >
            <icon name="save"/>
            Save
        </b-button>
    </div>
</template>

<script>
import Croppa from 'vue-croppa'

export default {
    name: 'ImageCropper',
    components: {
        croppa: Croppa.component,
    },
    props: {
        pictureUrl: {
            required: false,
            default: null,
        },
        hideSaveButton: {
            required: false,
            default: false,
        },
    },
    data () {
        return {
            croppa: {},
        }
    },
    methods: {
        onFileTypeMismatch () {
            this.$toasted.error('Invalid file type. Please choose an image.')
        },
        onFileSizeExceed () {
            this.$toasted.error(
                `The picture exceeds the maximum file size of ${this.$root.maxFileSizeBytes} bytes.`)
        },
        savePicture () {
            this.$emit('newPicture', this.croppa.generateDataUrl('image/png'))
        },
        getPicture () {
            return this.croppa.generateDataUrl('image/png')
        },
        refreshPicture () {
            this.croppa.refresh()
        },
    },
}
</script>

<style lang="sass">
.croppa-container
    background-color: $theme-dark-blue
    height: 100%
    width: 100%

.croppa-container:hover
    opacity: 1
    background-color: $theme-dark-blue
</style>
