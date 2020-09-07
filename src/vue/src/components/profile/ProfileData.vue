<template>
    <div>
        <b-modal
            ref="cropperModal"
            title="Edit profile picture"
            static
            hideFooter
            noEnforceFocus
        >
            <b-card class="no-hover">
                <cropper
                    v-if="profileImageDataURL"
                    ref="cropperRef"
                    :pictureUrl="profileImageDataURL"
                    @newPicture="fileHandler"
                />
            </b-card>
        </b-modal>
        <div class="profile-picture-lg">
            <img
                :src="storeProfilePic"
                class="theme-img"
            />
            <b-button @click="showCropperModal()">
                <icon name="edit"/>
                Edit
            </b-button>
        </div>
        <h4 class="theme-h4 mb-2 d-block">
            <span>User details</span>
        </h4>
        <b-card
            :class="$root.getBorderClass($route.params.uID)"
            class="no-hover multi-form"
        >
            <h2 class="theme-h2 field-heading multi-form">
                Username
            </h2>
            <b-form-input
                :readonly="true"
                :value="storeUsername"
                class="theme-input multi-form"
                type="text"
            />
            <h2 class="theme-h2 field-heading multi-form">
                Full name
            </h2>
            <b-form-input
                v-model="fullName"
                :readonly="(storeLtiID) ? true : false"
                class="theme-input multi-form"
                type="text"
                placeholder="Full name"
            />
            <h2 class="theme-h2 field-heading multi-form">
                Email address
            </h2>
            <email/>

            <b-button
                v-if="!storeLtiID"
                class="add-button float-right"
                @click="saveUserdata"
            >
                <icon name="save"/>
                Save
            </b-button>
            <b-button @click="downloadUserData">
                <icon name="download"/>
                Download Data
            </b-button>
        </b-card>
    </div>
</template>

<script>
import email from '@/components/profile/Email.vue'
import userAPI from '@/api/user.js'
import cropper from '@/components/assets/ImageCropper.vue'
import { mapGetters } from 'vuex'

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
        saveUserdata () {
            userAPI.update(0, { full_name: this.fullName }, { customSuccessToast: 'Saved profile data.' })
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
        isChanged () {
            return (this.fullName !== this.storeFullName)
        },
    },
}
</script>
