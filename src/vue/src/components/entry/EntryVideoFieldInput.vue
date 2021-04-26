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
                        v-b-modal="'video-upload-information-modal'"
                        class="fill-grey cursor-pointer"
                        name="info-circle"
                    />
                </b-input-group-text>
            </template>
        </b-input-group>

        <b-modal
            id="video-upload-information-modal"
            size="lg"
            title="Video upload information"
            hideFooter
            noEnforceFocus
        >
            <b-card class="no-hover">
                <template v-if="youtubeAllowed">
                    <!-- Steps taken from https://support.google.com/youtube/answer/57741 -->
                    <h2>YouTube</h2>

                    <ol>
                        <li>
                            Start watching or upload a video on
                            <b-link
                                class="text-blue"
                                href="https://youtube.com"
                                target="_blank"
                            >
                                youtube.com
                            </b-link>
                        </li>
                        <li>Under the video, click <b>Share</b> <icon name="share"/>.</li>
                        <li>
                            A panel will appear, presenting different sharing options. <br/>
                            <b>Copy the link</b>: Click the <b>Copy</b> button to copy a link to the video.
                        </li>
                    </ol>
                </template>

                <template v-if="kalturaAllowed">
                    <h2>Kaltura</h2>

                    <ol>
                        <li>
                            Navigate to your
                            <b-link
                                v-if="kalturaUrl"
                                class="text-blue"
                                :href="kalturaUrl"
                                target="_blank"
                            >
                                Kaltura environment
                            </b-link>
                            <span v-else>Kaltura environment</span>
                        </li>
                        <li>
                            Navigate to <b>My Media</b> and select the video you would like to share.
                            <img
                                src="/kaltura_media_selection.png"
                                class="inline-screenshot"
                            />
                            <br/><br/>
                        </li>
                        <li>Select the <b>Share</b> tab.</li>
                        <li>
                            Select the <b>Embed</b> tab and copy the embed code. Your video will only be visible to
                            those with access to your journal.

                            <img
                                src="/kaltura_embed_tab.png"
                                class="inline-screenshot"
                            />
                        </li>
                    </ol>
                </template>
            </b-card>
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
