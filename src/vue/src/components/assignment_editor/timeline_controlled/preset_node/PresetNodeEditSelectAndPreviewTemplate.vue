<template>
    <div class="mb-2">
        <b-form-group class="required">
            <template #label>
                Template
                <tooltip tip="The template students can use for this entry"/>
            </template>

            <b-input-group v-b-tooltip="(templates.length === 0) ? 'First create a template' : ''">
                <b-form-select
                    v-model="presetNode.template"
                    class="theme-select"
                    :disabled="templates.length === 0"
                    required
                    :invalid-feedback="templateInvalidFeedback"
                    :state="templateInputState"
                >
                    <option
                        disabled
                        value=""
                    >
                        Please select a template
                    </option>
                    <option
                        v-for="template in templates"
                        :key="template.id"
                        :value="template"
                    >
                        {{ template.name }}
                    </option>
                </b-form-select>

                <template #append>
                    <b-button
                        :class="{
                            'red-button': showTemplatePreview,
                            'green-button': !showTemplatePreview,
                        }"
                        :disabled="!presetNode.template"
                        @click="showTemplatePreview = !showTemplatePreview"
                    >
                        <icon :name="(showTemplatePreview) ? 'eye-slash' : 'eye'"/>
                        {{ (showTemplatePreview) ? 'Hide Preview' : 'Show Preview' }}
                    </b-button>
                </template>
            </b-input-group>
            <span
                class="text-blue cursor-pointer small"
                @click.stop="createTemplate({ fromPresetNode: presetNode })"
            >
                {{ (templates.length === 0) ? 'Create a new template' : 'Or create a new template' }}
            </span>
        </b-form-group>

        <div
            v-if="showTemplatePreview && presetNode.template"
            class="p-4 background-light-grey round-border"
        >
            <entry-preview :template="presetNode.template"/>
        </div>
    </div>
</template>

<script>
import EntryPreview from '@/components/entry/EntryPreview.vue'
import Tooltip from '@/components/assets/Tooltip.vue'

import { mapGetters, mapMutations } from 'vuex'

export default {
    components: {
        EntryPreview,
        Tooltip,
    },
    props: {
        presetNode: {
            required: true,
        },
    },
    data () {
        return {
            showTemplatePreview: false,
            templateInputState: null,
            templateInvalidFeedback: null,
        }
    },
    computed: {
        ...mapGetters({
            templates: 'template/assignmentTemplates',
        }),
    },
    watch: {
        'presetNode.template': 'validateTemplateInput',
    },
    methods: {
        ...mapMutations({
            createTemplate: 'assignmentEditor/CREATE_TEMPLATE',
        }),
        validateTemplateInput () {
            const template = this.presetNode.template

            if (template === null || template === '') {
                this.templateInputState = false
                this.templateInvalidFeedback = 'Template cannot be empty.'
            } else {
                this.templateInputState = null
            }
        },
    },
}
</script>
