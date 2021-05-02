<template>
    <iframe
        :key="`sandboxed-iframe-content-${renderKey}`"
        :srcdoc="content"
        sandbox="allow-same-origin allow-popups"
        height="0"
        frameBorder="0"
        marginwidth="0"
        marginheight="0"
        scrolling="no"
        class="w-100"
        @load="loadedIframe"
    />
</template>

<script>
import themeColors from 'sass/modules/colors.sass'

export default {
    name: 'SandboxedIframe',
    props: {
        content: {
            type: String,
            required: true,
        },
    },
    data () {
        return {
            iframe: null,
            renderKey: 0,
        }
    },
    watch: {
        content () {
            this.renderKey += 1
        },
    },
    methods: {
        loadedIframe (e) {
            this.iframe = e.target
            window.addEventListener('resize', this.fitContent)
            this.setCustomStyle()
            this.setLinkTarget()
            this.fitContent()
        },
        fitContent () {
            if (this.iframe && this.iframe.contentWindow) {
                this.iframe.height = 0
                this.iframe.height = this.iframe.contentWindow.document.body.scrollHeight
            }
        },
        setCustomStyle () {
            const css = `
body {
    font-family: 'Roboto', sans-serif;
    color: ${themeColors.textcolor};
    word-wrap: break-word;
}

body *:first-child{
    margin-top: 0px !important
}

body *:last-child{
    margin-bottom: 0px !important
}

p a {
    color: ${themeColors.blue};
}

img {
    max-width: 100%;
    border-radius: 5px;
    height: auto
}`
            const style = document.createElement('style')
            style.type = 'text/css'
            style.appendChild(document.createTextNode(css))
            this.iframe.contentWindow.document.head.append(style)
        },
        setLinkTarget () {
            const base = document.createElement('base')
            base.target = '_blank'
            this.iframe.contentWindow.document.head.append(base)
        },
    },
}
</script>
