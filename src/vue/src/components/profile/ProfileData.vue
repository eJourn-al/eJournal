<template>
    <div>
        <b-modal
            ref="cropperModal"
            title="Edit profile picture"
            static
            hideFooter
            noEnforceFocus
        >
            <cropper
                v-if="profileImageDataURL"
                ref="cropperRef"
                :pictureUrl="profileImageDataURL"
                @newPicture="fileHandler"
            />
        </b-modal>
        <div class="profile-picture-lg">
            <b-button
                class="position-absolute"
                pill
                @click="showCropperModal()"
            >
                <icon name="edit"/>
                Edit
            </b-button>
            <img
                :src="storeProfilePic"
                class="theme-img"
            />
        </div>
        <h2 class="theme-h2 field-heading mb-2">
            Username
        </h2>
        <b-form-input
            :disabled="true"
            :value="storeUsername"
            class="mb-2"
            type="text"
        />
        <h2 class="theme-h2 field-heading mb-2">
            Full name
        </h2>
        <b-input-group class="mb-2">
            <b-form-input
                v-model="fullName"
                :disabled="storeLtiID"
                :class="{ 'no-right-radius': !storeLtiID }"
                type="text"
                placeholder="Full name"
            />
            <b-button
                v-if="!storeLtiID"
                slot="append"
                class="green-button"
                @click="saveFullName"
            >
                <icon name="save"/>
                Save
            </b-button>
        </b-input-group>
        <h2 class="theme-h2 field-heading mb-2">
            Email address
        </h2>
        <email/>

        <div class="mt-2">
            <b-button click="downloadUserData">
                <icon name="download"/>
                Download Data
            </b-button>
        </div>
    </div>
</template>

<script>
import { mapGetters } from 'vuex'
import cropper from '@/components/assets/ImageCropper.vue'
import email from '@/components/profile/Email.vue'
import userAPI from '@/api/user.js'

export default {
    components: {
        email,
        cropper,
    },
    data () {
        return {
            file: null,
            profileImageDataURL: null,
            showEmailValidationInput: true,
            emailVerificationToken: null,
            emailVerificationTokenMessage: null,
            fullName: null,
            updateCropper: false,
        }
    },
    computed: {
        ...mapGetters({
            storeUsername: 'user/username',
            storeLtiID: 'user/ltiID',
            storeProfilePic: 'user/profilePicture',
            storeFullName: 'user/fullName',
        }),
    },
    mounted () {
        this.profileImageDataURL = this.storeProfilePic
        this.fullName = this.storeFullName
    },
    methods: {
        showCropperModal () {
            this.$refs.cropperRef.refreshPicture()
            this.$refs.cropperModal.show()
        },
        saveFullName () {
            userAPI.update(0, { full_name: this.fullName }, { customSuccessToast: 'Saved full name.' })
                .then(() => {
                    this.$store.commit('user/SET_FULL_USER_NAME', { fullName: this.fullName })
                })
        },
        fileHandler (dataURL) {
            userAPI.updateProfilePictureBase64(dataURL, { customSuccessToast: 'Profile picture updated.' })
                .then((resp) => {
                    this.$store.commit('user/SET_PROFILE_PICTURE', resp.data.download_url)
                    this.profileImageDataURL = resp.data.download_url
                    this.$refs.cropperModal.hide()
                })
        },
        downloadUserData () {
            userAPI.GDPR(0)
                .then((response) => {
                    try {
                        const blob = new Blob([response.data], { type: response.headers['content-type'] })
                        const link = document.createElement('a')
                        link.href = window.URL.createObjectURL(blob)
                        link.download = `${this.storeUsername}_all_user_data.zip`
                        document.body.appendChild(link)
                        link.click()
                        link.remove()
                    } catch (_) {
                        this.$toasted.error('Error creating file locally.')
                    }
                })
        },
    },
}
</script>
