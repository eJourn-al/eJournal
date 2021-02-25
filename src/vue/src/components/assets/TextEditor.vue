<!-- Custom wrapper for tinymce editor -->
<!-- If more events are desired, here is an overview: https://www.tiny.cloud/docs/advanced/events/ -->

<template>
    <div
        :ref="`ref-${id}`"
        class="editor-container"
    >
        <div
            :id="id"
            :placeholder="placeholder"
        />
    </div>
</template>

<script>
/* eslint-disable */
import tinymce from 'tinymce/tinymce' /* Needs to occur before icons and themes */
import 'tinymce/icons/default'
import 'tinymce/themes/silver'

/* Only works with basic lists enabled. */
import 'tinymce/plugins/advlist'
import 'tinymce/plugins/autolink'
import 'tinymce/plugins/autoresize'
/* Allows direct manipulation of the html aswell as easy export. */
import 'tinymce/plugins/code'
import 'tinymce/plugins/fullscreen'
import 'tinymce/plugins/hr'
import 'tinymce/plugins/image'
import 'tinymce/plugins/imagetools'
import 'tinymce/plugins/link'
import 'tinymce/plugins/lists'
import 'tinymce/plugins/nonbreaking'
import 'tinymce/plugins/paste'
import 'tinymce/plugins/preview'
import 'tinymce/plugins/print'
import 'tinymce/plugins/searchreplace'
import 'tinymce/plugins/spellchecker'
import 'tinymce/plugins/table'
import 'tinymce/plugins/textpattern'
/* Table of contents. */
import 'tinymce/plugins/toc'
import 'tinymce/plugins/wordcount'
/* eslint-enable */

import 'public/tinymce/plugins/placeholder.js'

import auth from '@/api/auth.js'

import themeColors from 'sass/modules/colors.sass'

export default {
    name: 'TextEditor',
    props: {
        limitedColors: {
            type: Boolean,
            default: false,
        },
        basic: {
            type: Boolean,
            default: false,
        },
        /* Used to bind the editor to the components text area. */
        id: {
            type: String,
            required: true,
        },
        value: {
            type: String,
            default: '',
        },
        placeholder: {
            type: String,
            default: '',
        },
        inline: {
            default: false, // NOTE: Does not play nice with bootstrap modals
        },
        displayInline: {
            default: false,
        },
        minifiedTextArea: {
            default: false,
        },
        footer: {
            default: true,
        },
        autofocus: {
            default: false,
        },
    },
    data () {
        return {
            uploading: 0,
            content: '',
            editor: null,
            justFocused: false,
            valueSet: false,
            config: {
                selector: `#${this.id}`,
                init_instance_callback: this.editorInit,

                /* Style */
                // QUESTION: How the bloody hell do we make this available with webpack so we can use node modules,
                // whilst also predetermining the correct url before bundling?.
                skin_url: '/tinymce/skins/ui/oxide',
                /* Custom style applied to the content of the editor */
                content_css: '/tinymce/content.css',

                menubar: true,
                branding: false,
                statusbar: true,
                inline: this.inline,
                resize: true,

                /* File handling */
                image_title: true,
                paste_data_images: true,
                images_upload_handler: this.imageUploadHandler,

                /* Editor size */
                min_height: 260,
                max_height: 500,
                autoresize_bottom_margin: 10,

                /* Link handling */
                link_assume_external_targets: true,
                default_link_target: '_blank',

                placeholder_attrs: {
                    style: {
                        position: 'absolute',
                        top: '0px',
                        left: 0,
                        color: '#888',
                        padding: '13px 0 0 6px',
                        overflow: 'hidden',
                        'font-family': 'Roboto',
                        'white-space': 'pre-wrap',
                    },
                },
            },
            basicConfig: {
                toolbar1: 'bold italic underline alignleft aligncenter alignright alignjustify '
                    + '| forecolor backcolor | formatselect | bullist numlist | image table '
                    + '| link removeformat fullscreentoggle fullscreen',
                plugins: [
                    'placeholder link autoresize paste image lists wordcount autolink',
                    'table fullscreen',
                ],
            },
            extensiveConfig: {
                toolbar1: 'bold italic underline alignleft aligncenter alignright alignjustify | forecolor backcolor '
                    + '| formatselect | bullist numlist | image table | link removeformat fullscreentoggle fullscreen',
                plugins: [
                    'placeholder link preview paste print hr lists advlist wordcount autolink',
                    'autoresize code fullscreen image imagetools',
                    'searchreplace table toc',
                ],
            },
            extensiveConfigMenu: {
                menu: {
                    file: { title: 'File', items: 'newdocument print' },
                    edit: { title: 'Edit', items: 'undo redo | cut copy paste | code | selectall searchreplace' },
                    insert: { title: 'Insert', items: 'image link | hr | toc' },
                    view: { title: 'View', items: 'preview fullscreen' },
                    format: {
                        title: 'Format',
                        items: 'bold italic underline strikethrough superscript subscript '
                            + '| blockformats align | removeformat',
                    },
                    table: { title: 'Table', items: 'inserttable tableprops deletetable | cell row column' },
                },
            },
            fullScreenButton: null,
        }
    },
    watch: {
        content (value) {
            this.$emit('input', value)
        },
        value (value) {
            this.initValue(value)
        },
    },
    mounted () {
        this.config.statusbar = this.footer

        if (this.basic) {
            this.setBasicConfig()
        } else {
            this.setExtensiveConfig()
        }

        if (this.limitedColors) {
            this.setCustomColors()
        }

        if (this.minifiedTextArea) { this.minifyTextArea() }

        this.enableTabs()
        this.enableBrowserSpellchecker()
        this.enableMarkdownPatterns()

        tinymce.init(this.config)

        if (this.autofocus) { this.setFocus() }
    },
    beforeDestroy () {
        try {
            if (this.editor) { tinymce.remove(this.editor) }
        } catch (NS_ERROR_UNEXPECTED) {
            // NOTE: User behaviour is not interrupted by this error
            // TODO: When we have time, figure out the underlying issue
        }
    },
    methods: {
        initValue (value) {
            if (value && this.editor && !this.valueSet && (value !== this.content)) {
                let separatedContent = ''
                if (this.content) {
                    separatedContent = this.content.startsWith('<p>') ? this.content : `<p>${this.content}</p>`
                }
                this.content = `${value}${separatedContent}`
                this.editor.setContent(`${value}${separatedContent}`)
                this.valueSet = true
            }
        },
        editorInit (editor) {
            const vm = this
            this.editor = editor

            this.setupEventHandlers(editor)
            if (this.displayInline) { this.setupInlineDisplay(editor) }

            editor.on('Change', () => { vm.content = this.editor.getContent() })

            editor.on('KeyUp', (e) => {
                vm.handleShortCuts(e)
                vm.content = this.editor.getContent()
            })

            vm.initValue(vm.value)
        },
        setupEventHandlers (editor) {
            editor.on('focus', () => { this.$emit('editor-focus') })
            editor.on('blur', () => { this.$emit('editor-blur') })
        },
        setupInlineDisplay (editor) {
            const container = this.$refs[`ref-${this.id}`]

            container.querySelector('div.tox-editor-header').style.display = 'none'
            if (this.footer) { container.querySelector('div.tox-statusbar').style.display = 'none' }

            editor.on('focus', () => {
                this.justFocused = true
                setTimeout(() => { this.justFocused = false }, 20)
                container.querySelector('div.tox-editor-header').style.display = 'block'
                if (this.footer) { container.querySelector('div.tox-statusbar').style.display = 'flex' }
            })

            editor.on('blur', () => {
                if (this.justFocused) { return }
                container.querySelector('div.tox-editor-header').style.display = 'none'
                if (this.footer) { container.querySelector('div.tox-statusbar').style.display = 'none' }
            })
        },
        handleShortCuts (e) {
            if (this.editor.plugins.fullscreen.isFullscreen() && e.key === 'Escape') {
                this.editor.execCommand('mceFullScreen', { skip_focus: true })
            }
        },
        /*
            * Blob info consists of:
            * blobInfo.id(): blobid -- 'blobidXXX'
            * blobInfo.name(): filename -- 'some_img'
            * blobInfo.blob(): javascript file object
            * blobInfo.filename() filename with extension -- 'some_img.jpg'
        */
        imageUploadHandler (blobInfo, success, failure) {
            const file = blobInfo.blob()
            const formData = new FormData()

            if (file.size > this.$root.maxFileSizeBytes) {
                failure(`The selected file exceeds the maximum file size of: ${this.$root.maxSizeBytes} bytes.`)
            } else {
                formData.append('in_rich_text', true)
                formData.append('file', file)
                this.uploading += 1
                this.$emit('startedUploading')
                auth.uploadFile('files', formData)
                    .then((response) => { success(response.data.download_url) })
                    .catch(() => { failure('File upload failed') })
                    .finally(() => {
                        this.uploading -= 1
                        this.$emit('finishedUploading')
                    })
            }
        },
        insertDataURL () {
            const input = document.createElement('input')
            input.setAttribute('type', 'file')
            input.setAttribute('accept', 'image/*')

            input.onchange = () => {
                const files = this.files
                if (!files || !files.length) { return }

                const file = files[0]
                if (files[0].size > this.$root.maxFileSizeBytes) {
                    this.$toasted.error(
                        `The selected image exceeds the maximum file size of ${this.$root.maxFileSizeBytes} bytes.`)
                    return
                }

                const reader = new FileReader()
                reader.onload = () => {
                    const dataURL = reader.result
                    this.editor.insertContent(`<img src="${dataURL}"/>`)
                }
                reader.readAsDataURL(file)
            }
            input.click()
        },
        setCustomColors () {
            /* Enables some basic colors to chose from, inline with the websites theme colors.
             * Strips the leading # of the color codes */
            this.config.color_map = [
                themeColors.darkblue.substring(1), 'Theme dark blue',
                themeColors.green.substring(1), 'Theme positive selected',
                themeColors.oranga.substring(1), 'Theme change selected',
                themeColors.red.substring(1), 'Theme negative selected',
            ]
            this.config.custom_colors = false
        },
        setBasicConfig () {
            this.config.menubar = false
            this.config.toolbar1 = this.basicConfig.toolbar1
            this.config.plugins = this.basicConfig.plugins
        },
        setExtensiveConfig () {
            this.config.menubar = true
            this.config.toolbar1 = this.extensiveConfig.toolbar1
            this.config.plugins = this.extensiveConfig.plugins
            this.config.menu = this.extensiveConfigMenu.menu
        },
        minifyTextArea () {
            this.config.min_height = 10
            this.config.max_height = 260
            this.config.autoresize_bottom_margin = 0.1
            this.config.placeholder_attrs.style.left = 6
        },
        enableTabs () {
            /* Three space tabs, breaks tabbing through table entries (choice) */
            this.config.plugins.push('nonbreaking')
            this.config.nonbreaking_force_tab = true
        },
        enableBrowserSpellchecker () {
            this.config.plugins.push('spellchecker')
            this.config.browser_spellcheck = true
        },
        enableMarkdownPatterns () {
            this.config.plugins.push('textpattern')
            this.config.textpattern_patterns = [
                { start: '*', end: '*', format: 'italic' },
                { start: '**', end: '**', format: 'bold' },
                { start: '#', format: 'h1' },
                { start: '##', format: 'h2' },
                { start: '###', format: 'h3' },
                { start: '####', format: 'h4' },
                { start: '#####', format: 'h5' },
                { start: '######', format: 'h6' },
                { start: '1. ', cmd: 'InsertOrderedList' },
                { start: '* ', cmd: 'InsertUnorderedList' },
                { start: '- ', cmd: 'InsertUnorderedList' },
            ]
        },
        /* NOTE: Called from parent. */
        clearContent () {
            this.editor.setContent('')
            this.content = ''
        },
        /* NOTE: Also called from parent. */
        setFocus () {
            /* Focuses the editor once available, and sets the cursor at the end of the text */
            if (this.editor) {
                this.editor.fire('focus')
                this.editor.selection.select(this.editor.getBody(), true)
                this.editor.selection.collapse(false)
            } else {
                window.setTimeout(this.setFocus, 20)
            }
        },
    },
}
</script>

<style lang="sass">
@import '~sass/partials/shadows.sass'

.editor-container
    border-radius: 5px !important
    padding-right: 1px
    width: 100%
    .tox-tinymce
        border-radius: 5px !important
        font-family: 'Roboto'
    .tox-edit-area
        border-radius: 0px !important
        &::before
            @extend .small-inner-shadow
            content: ''
            position: absolute
            z-index: 2
            top: 0
            right: 0
            bottom: 0
            left: 0
            pointer-events: none

div.mce-fullscreen
    padding-top: $header-height

.modal .mce-fullscreen
    padding-top: 0px
</style>
