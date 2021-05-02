<template>
    <!-- eslint-disable vue/attribute-hyphenation -->
    <b-form-group
        :state="state"
        :invalid-feedback="invalidFeedback"
    >
        <b-input-group>
            <b-form-textarea
                v-if="kalturaAllowed"
                v-model="data"
                :placeholder="placeholder"
                class="theme-input"
                type="text"
                trim
            />
            <b-form-input
                v-else
                v-model="data"
                :placeholder="placeholder"
                class="theme-input"
                type="text"
                trim
            />

            <template #append>
                <b-input-group-text>
                    <icon
                        v-b-modal="'video-embed-instructions-modal'"
                        class="fill-grey cursor-pointer"
                        name="info-circle"
                    />
                </b-input-group-text>
            </template>
        </b-input-group>

        <b-modal
            id="video-embed-instructions-modal"
            size="lg"
            title="Video embed instructions"
            hideFooter
            show
            noEnforceFocus
        >
            <template v-if="youtubeAllowed">
                <!-- Steps taken from https://support.google.com/youtube/answer/57741 -->
                <b-alert
                    show
                    variant="danger"
                    class="mb-2"
                >
                    <h2 class="theme-h2 field-heading">
                        <icon
                            name="brands/youtube"
                            class="shift-up-2 fill-red mr-1"
                        />
                        YouTube
                    </h2>
                </b-alert>
                <ol class="mb-2">
                    <li>
                        Navigate to
                        <b-link
                            class="text-blue"
                            href="https://youtube.com"
                            target="_blank"
                        >
                            https://www.youtube.com
                        </b-link>
                        .
                    </li>
                    <li>
                        Select or upload the video you would like to share.
                    </li>
                    <li>
                        Under the video, click <b>Share</b>
                        <icon
                            name="share"
                            class="shift-up-2 ml-1"
                            scale="0.8"
                        />.
                    </li>
                    <li>
                        From the presented sharing options, click the <b>copy</b> button to copy a link to the video.
                    </li>
                </ol>
            </template>

            <template v-if="kalturaAllowed">
                <b-alert
                    show
                    class="mb-2 purple-alert"
                >
                    <h2 class="theme-h2 field-heading">
                        <icon
                            name="photo-video"
                            class="shift-up-2 mr-1"
                        />
                        Kaltura
                    </h2>
                </b-alert>
                <ol class="mb-2">
                    <li>
                        Navigate to
                        <b-link
                            v-if="kalturaUrl"
                            class="text-blue"
                            :href="kalturaUrl"
                            target="_blank"
                        >
                            {{ kalturaUrl }}
                        </b-link>
                        <template v-else>
                            your Kaltura environment
                        </template>.
                    </li>
                    <li>
                        Navigate to <b>My Media</b>.
                    </li>
                    <li>
                        Select or upload the video you would like to share.
                        <img
                            src="/kaltura_media_selection.png"
                            class="inline-screenshot bordered-content mb-2"
                        />
                    </li>
                    <li>
                        Select the <b>Share</b> tab.
                        <img
                            src="/kaltura_embed_tab.png"
                            class="inline-screenshot bordered-content mb-2"
                        />
                    </li>
                    <li>
                        Select the <b>Embed</b> tab and copy the embed code.
                        <small class="d-block mb-2">
                            <b>
                                Note:
                            </b>
                            Your video will only be visible to those with access to your journal.
                        </small>
                    </li>
                </ol>
            </template>
        </b-modal>
    </b-form-group>
    <!-- eslint-enable vue/attribute-hyphenation -->
</template>

<script>
import validation from '@/utils/validation.js'

import { mapGetters } from 'vuex'

export default {
    props: {
        value: {
            required: true,
        },
        field: {
            required: true,
        },
    },
    data () {
        return {
            state: null,
            invalidFeedback: null,
        }
    },
    computed: {
        ...mapGetters({
            kalturaUrl: 'instance/kalturaUrl',
        }),
        data: {
            get () { return this.value },
            set (value) { this.$emit('input', value) },
        },
        youtubeAllowed () { return this.field.options.split(',').includes('y') },
        kalturaAllowed () { return this.field.options.split(',').includes('k') },
        placeholder () {
            if (this.youtubeAllowed && this.kalturaAllowed) {
                return 'Enter a YouTube video URL or a Kaltura video embed code'
            } else if (this.youtubeAllowed) {
                return 'Enter a YouTube video URL'
            } else if (this.kalturaAllowed) {
                return 'Enter a Kaltura video embed code'
            } else {
                this.$store.commit('sentry/CAPTURE_SCOPED_MESSAGE', {
                    msg: 'Video host incorrectly configured.',
                    extra: { field: this.field, data: this.value },
                })
                return 'Unknown video host configured, contact your teacher'
            }
        },
    },
    watch: {
        data (val) {
            let validated = false

            if (this.youtubeAllowed && this.kalturaAllowed) {
                validated = validation.validateYouTubeUrlWithVideoID(val)
                validated = validated || validation.validateKalturaEmbedCode(val)

                this.invalidFeedback = 'Provide a valid YouTube video URL or a Kaltura video embed code'
            } else if (this.youtubeAllowed) {
                validated = validation.validateYouTubeUrlWithVideoID(val)
                this.invalidFeedback = 'Enter a valid YouTube video URL'
            } else if (this.kalturaAllowed) {
                validated = validation.validateKalturaEmbedCode(val)
                this.invalidFeedback = 'Enter a valid Kaltura embed code'
            } else {
                this.invalidFeedback = 'Unknown video host configured, if this issue perists, contact your teacher'
            }

            this.state = validated
        },
    },
}
</script>

<style lang="sass">
.inline-screenshot
    max-width: 100%
    height: auto
</style>
