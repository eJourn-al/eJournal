<template>
    <b-embed
        v-if="validatedSrc(data)"
        :src="validatedSrc(data)"
        type="iframe"
        aspect="16by9"
        allowfullscreen
    />
    <span
        v-else
    >
        {{ data }}
    </span>
</template>

<script>
import genericUtils from '@/utils/generic_utils.js'

export default {
    props: {
        data: {
            required: true,
            type: String,
        },
        field: {
            required: true,
            type: Object,
        },
    },
    computed: {
        youtubeAllowed () { return this.field.options.split(',').includes('y') },
        kalturaAllowed () { return this.field.options.split(',').includes('k') },
    },
    methods: {
        validatedSrc () {
            const youtubeId = genericUtils.parseYouTubeVideoID(this.data)
            const kalturaEmbedCodeSrc = genericUtils.praseSrcFromKalturaEmbedCode(this.data)

            if (this.youtubeAllowed && this.kalturaAllowed && (youtubeId || kalturaEmbedCodeSrc)) {
                if (youtubeId) {
                    return `https://www.youtube.com/embed/${youtubeId}?rel=0&amp;showinfo=0`
                } else {
                    return kalturaEmbedCodeSrc
                }
            } else if (this.youtubeAllowed && youtubeId) {
                return `https://www.youtube.com/embed/${youtubeId}?rel=0&amp;showinfo=0`
            } else if (this.kalturaAllowed && kalturaEmbedCodeSrc) {
                return kalturaEmbedCodeSrc
            } else {
                this.$store.commit('sentry/CAPTURE_SCOPED_MESSAGE', {
                    level: 'warning',
                    msg: 'A video field contained invalid data.',
                    extra: {
                        data: this.data,
                        field: this.field,
                    },
                })

                return null
            }
        },
    },
}
</script>
