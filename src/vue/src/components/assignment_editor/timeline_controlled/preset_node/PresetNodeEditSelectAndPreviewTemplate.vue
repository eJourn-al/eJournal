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
        </b-form-group>

        <span
            class="text-blue cursor-pointer"
            @click.stop="createTemplate({ fromPresetNode: presetNode })"
        >
            {{ (templates.length === 0) ? 'Create a new template' : 'Or create a new template' }}
        </span>

        <div
            v-if="showTemplatePreview && presetNode.template"
            class="p-2"
        >
            <entry-preview
                :presetNode="presetNode"
                :template="presetNode.template"
            />
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
        }
    },
    computed: {
        ...mapGetters({
            templates: 'template/assignmentTemplates',
        }),
    },
    methods: {
        ...mapMutations({
            createTemplate: 'assignmentEditor/CREATE_TEMPLATE',
        }),
    },
}
</script>
