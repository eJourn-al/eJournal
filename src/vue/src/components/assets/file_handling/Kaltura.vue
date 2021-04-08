<template>
<!-- eslint-disable -->
    <div>
        <b-textarea
            v-model="input"
            placeholder="Paste your kaltura embed information"
            strip
        />

        {{ src }}

        <!-- <iframe
            id="kaltura_player"
            src="https://api.eu.kaltura.com/p/120/sp/12000/embedIframeJs/uiconf_id/23449960/partner_id/120?iframeembed=true&playerId=kaltura_player&entry_id=0_gzmsms1t&flashvars[streamerType]=auto&amp;flashvars[localizationCode]=en_US&amp;flashvars[leadWithHTML5]=true&amp;flashvars[sideBarContainer.plugin]=true&amp;flashvars[sideBarContainer.position]=left&amp;flashvars[sideBarContainer.clickToClose]=true&amp;flashvars[chapters.plugin]=true&amp;flashvars[chapters.layout]=vertical&amp;flashvars[chapters.thumbnailRotator]=false&amp;flashvars[streamSelector.plugin]=true&amp;flashvars[EmbedPlayer.SpinnerTarget]=videoHolder&amp;flashvars[dualScreen.plugin]=true&amp;flashvars[hotspots.plugin]=1&amp;flashvars[Kaltura.addCrossoriginToIframe]=true&amp;&wid=0_rv1htil5"
            width="400"
            height="261"
            allowfullscreen
            webkitallowfullscreen
            mozAllowFullScreen
            allow="autoplay *; fullscreen *; encrypted-media *"
            sandbox="allow-forms allow-same-origin allow-scripts allow-top-navigation allow-pointer-lock allow-popups allow-modals allow-orientation-lock allow-popups-to-escape-sandbox allow-presentation allow-top-navigation-by-user-activation"
            frameborder="0"
            title="Kaltura Player"
        /> -->

        <b-embed
            :src="src"
            type="iframe"
            aspect="16by9"
            allowfullscreen
        />

        <!-- <iframe
            id="kaltura_player"
            src="https://video.uva.nl/media/test+-+published/0_ye1cdzka"
            width="400"
            height="261"
            allowfullscreen
            webkitallowfullscreen
            mozAllowFullScreen
            allow="autoplay *; fullscreen *; encrypted-media *"
            sandbox="allow-forms allow-same-origin allow-scripts allow-top-navigation allow-pointer-lock allow-popups allow-modals allow-orientation-lock allow-popups-to-escape-sandbox allow-presentation allow-top-navigation-by-user-activation"
            frameborder="0"
            title="Kaltura Player"
        /> -->
    </div>
</template>

<script>
export default {
    data () {
        return {
            input: '',
            a: 1,
            kalturaSrcRegex: /(?:<iframe.*src=")(https:\/\/api\.eu\.kaltura\.com.*)(?:" width)/,
        }
    },
    computed: {
        src () {
            if (!this.input) { return null }

            const match = this.input.match(this.kalturaSrcRegex)

            return match ? match[1] : null
            // // This approach does not include all flashvars which are needed for some reason
            // const parser = new DOMParser()
            // const parsedIframe = parser.parseFromString(this.input, 'text/html')
            // const iFrame = parsedIframe.getElementsByTagName('iframe')
            // return iFrame[0].src
        },
    },
}
</script>

// unlisted
// https://video.uva.nl/media/test+-+unlisted/0_gzmsms1t

// listed
// https://video.uva.nl/media/test+-+published/0_ye1cdzka
