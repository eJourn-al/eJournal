<template>
    <b-card
        class="field-card"
    >
        <b-row
            alignH="between"
            noGutters
        >
            <b-col
                cols="12"
                sm="10"
                lg="11"
            >
                <b-input
                    v-model="field.title"
                    class="mb-2"
                    placeholder="Optional field title"
                    required
                />
                <text-editor
                    v-if="showEditors"
                    :id="`rich-text-editor-field-${field.location}`"
                    :key="`rich-text-editor-field-${field.location}`"
                    v-model="field.description"
                    :basic="true"
                    :displayInline="true"
                    :minifiedTextArea="true"
                    class="mb-2"
                    placeholder="Optional description"
                    required
                />
                <div class="d-flex">
                    <b-select
                        v-model="field.type"
                        :options="fieldTypes"
                        class="theme-select mb-2 mr-2"
                        @change="selectedType"
                    />
                    <b-button
                        v-if="!field.required"
                        class="optional-field-template float-right mb-2"
                        :class="{ 'input-disabled': field.type === 'n' }"
                        @click.stop
                        @click="field.required = !field.required"
                    >
                        <icon name="asterisk"/>
                        Optional
                    </b-button>
                    <b-button
                        v-if="field.required"
                        class="required-field-template float-right mb-2"
                        @click.stop
                        @click="field.required = !field.required"
                    >
                        <icon name="asterisk"/>
                        Required
                    </b-button>
                </div>

                <!-- Field Options -->
                <div v-if="field.type === 'f'">
                    <b-select
                        v-model="selectedExtensionType"
                        :options="fileExtensions"
                        placeholder="Custom"
                        class="theme-select mb-2 mr-2"
                        @change="selectedExtensionType === ' ' || selectedExtensionType === '*' ?
                            field.options = '' : field.options = selectedExtensionType"
                    />
                    <b-input
                        v-if="selectedExtensionType == ' '"
                        v-model="field.options"
                        placeholder="Enter a list of accepted extensions (comma seperated), for example: pdf, docx"
                        @input="selectedExtensionType = ' '"
                    />
                </div>
                <theme-select
                    v-if="field.type === 'v'"
                    v-model="selectedVideoSources"
                    label="label"
                    trackBy="id"
                    :options="videoSources"
                    :multiple="true"
                    placeholder="Please select one or more video hosts"
                    :multiSelectText="selectedVideoSources.map(host => host.label).join(', ')"
                    :showCount="false"
                    class="mb-2 mr-2"
                    @input="field.options = selectedVideoSources.map(elem => elem.id).join()"
                />
                <div v-else-if="field.type === 's'">
                    <!-- Event targeting allows us to access the input value -->
                    <div class="d-flex">
                        <b-input
                            class="mb-2 mr-2"
                            placeholder="Enter an option"
                            @keyup.enter.native="addSelectionOption($event.target, field)"
                        />
                        <b-button
                            class="float-right mb-2 green-button"
                            @click.stop="addSelectionOption($event.target.previousElementSibling, field)"
                        >
                            <icon name="plus"/>
                            Add
                        </b-button>
                    </div>
                    <div v-if="field.options">
                        <b-button
                            v-for="(option, index) in JSON.parse(field.options)"
                            :key="index"
                            class="red-button mr-2 mb-2"
                            @click.stop="removeSelectionOption(option, field)"
                        >
                            <icon name="trash"/>
                            {{ option }}
                        </b-button>
                    </div>
                </div>
                <small
                    v-else-if="field.type === 'n'"
                >
                    <b>Note:</b> Students cannot provide any input for this field.
                    The title and / or description above can be used to provide additional instructions within your
                    template.
                </small>
            </b-col>
            <b-col
                cols="12"
                sm="2"
                lg="1"
                class="icon-box"
            >
                <div class="handle d-inline d-sm-block">
                    <icon
                        class="move-icon"
                        name="arrows-alt"
                        scale="1.25"
                    />
                </div>
                <icon
                    class="trash-icon"
                    name="trash"
                    scale="1.25"
                    @click.native="$emit('removeField', field.location)"
                />
            </b-col>
        </b-row>
    </b-card>
</template>

<script>
export default {
    name: 'TemplateField',
    components: {
        TextEditor: () => import(/* webpackChunkName: 'text-editor' */ '@/components/assets/TextEditor.vue'),
    },
    props: {
        field: {
            required: true,
        },
        showEditors: {
            default: true,
        },
    },
    data () {
        const fileExtensions = { '*': 'Accept Any Extension' }
        fileExtensions[this.$root.fileTypes.img] = 'Accept Images Only'
        fileExtensions[this.$root.fileTypes.pdf] = 'Accept PDF Only'
        fileExtensions[' '] = 'Accept Custom Extensions Only'

        const youtube = { label: 'YouTube', id: 'y' }
        const kaltura = { label: 'Kaltura', id: 'k' }

        return {
            fieldTypes: {
                t: 'Text',
                rt: 'Rich Text',
                f: 'File Upload',
                v: 'Video',
                u: 'URL',
                d: 'Date',
                dt: 'Date Time',
                s: 'Selection',
                n: 'No Submission (Description Only)',
            },
            fileExtensions,
            selectedExtensionType: '',
            youtube,
            kaltura,
            videoSources: [youtube, kaltura],
            selectedVideoSources: [youtube, kaltura],
        }
    },
    watch: {
        field () {
            this.setFieldExtensionType()
        },
    },
    created () {
        this.setFieldExtensionType()
        this.initAndMapSelectedVideoSources()
    },
    methods: {
        setFieldExtensionType () {
            /* Set the field extension to the proper value */
            if (this.field.type === 'f') {
                if (!this.field.options) {
                    this.selectedExtensionType = '*'
                } else if (Object.keys(this.fileExtensions).includes(this.field.options)) {
                    this.selectedExtensionType = this.field.options
                } else {
                    this.selectedExtensionType = ' '
                }
            }
        },
        /* Work back from the fetched video source options as string to the respective objects for the select */
        initAndMapSelectedVideoSources () {
            if (this.field.type === 'v') {
                this.selectedVideoSources = this.field.options.split(',').map(
                    (id) => this.videoSources.find((source) => source.id === id),
                )
            }
        },
        selectedType () {
            this.field.options = ''
            this.selectedExtensionType = ''
            if (this.field.type === 'n') {
                this.field.required = false
            } else if (this.field.type === 'v') {
                this.field.options = this.videoSources.map((source) => source.id).join()
            }
        },
        addSelectionOption (target, field) {
            if (target.value.trim()) {
                if (!field.options) {
                    field.options = JSON.stringify([])
                }
                const options = JSON.parse(field.options)
                options.push(target.value.trim())
                field.options = JSON.stringify(options)
                target.value = ''
                target.focus()
            }
        },
        removeSelectionOption (option, field) {
            const options = JSON.parse(field.options)
            options.splice(options.indexOf(option.trim()), 1)
            field.options = JSON.stringify(options)
        },
    },
}
</script>
