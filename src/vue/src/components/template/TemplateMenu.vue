<template>
    <div
        v-intro="'Every assignment contains customizable <i>templates</i> which specify what the contents of \
        each journal entry should be. There are two different types of templates:<br/><br/><ul><li><b>\
        Unlimited templates</b> can be freely used by students as often as they want</li><li><b>Preset-only \
        templates</b> can be used only for preset entries that you add to the timeline</li></ul>You can \
        preview and edit a template by clicking on it.'"
        v-intro-step="2"
    >
        <h3 class="theme-h3">
            Entry Templates
        </h3>

        <div class="d-block">
            <b-card
                :class="$root.getBorderClass($route.params.cID)"
                class="no-hover"
            >
                <div
                    v-if="templates.length > 0"
                    class="template-list-header"
                >
                    <b class="float-right">
                        Type
                    </b>
                    <b>Name</b>
                </div>

                <template-menu-item
                    v-for="template in templates"
                    :key="`template-${template.id}-menu-item`"
                    :template="template"
                    @delete-template="deleteTemplate($event)"
                    @select-template="selectTemplate({ template: $event })"
                />

                <b-button
                    class="green-button mt-2 full-width"
                    @click="newTemplate()"
                >
                    <icon name="plus"/>
                    Create New Template
                </b-button>

                <b-button
                    class="orange-button mt-2 full-width"
                    @click.stop="setActiveComponent(activeComponentOptions.templateImport)"
                >
                    <icon name="file-import"/>
                    Import Template
                </b-button>
            </b-card>
        </div>
    </div>
</template>

<script>
import TemplateMenuItem from '@/components/template/TemplateMenuItem.vue'

import { mapActions, mapGetters, mapMutations } from 'vuex'

export default {
    name: 'TemplateMenu',
    components: {
        TemplateMenuItem,
    },
    computed: {
        ...mapGetters({
            templates: 'template/assignmentTemplates',
            activeComponent: 'assignmentEditor/activeComponent',
            activeComponentOptions: 'assignmentEditor/activeComponentOptions',
            selectedTemplate: 'assignmentEditor/selectedTemplate',
            templateDraft: 'assignmentEditor/templateDraft',
        }),
    },
    methods: {
        ...mapMutations({
            selectTemplate: 'assignmentEditor/selectTemplate',
            createTemplate: 'assignmentEditor/createTemplate',
            setActiveComponent: 'assignmentEditor/setActiveComponent',
        }),
        ...mapActions({
            delete: 'template/delete',
            templateDeleted: 'assignmentEditor/templateDeleted',
        }),
        newTemplate () {
            if (this.templateDraft) {
                this.selectTemplate({ template: this.templateDraft })
            } else {
                const template = {
                    field_set: [{
                        type: 'rt',
                        title: 'Content',
                        description: '',
                        options: null,
                        location: 0,
                        required: true,
                    }],
                    name: 'Entry',
                    id: -1,
                    preset_only: false,
                    fixed_categories: true,
                }

                this.createTemplate({ template })
            }
        },
        deleteTemplate (template) {
            if (window.confirm(
                `Are you sure you want to delete template "${template.name}" from this assignment?`)) {
                this.delete({ id: template.id, aID: this.$route.params.aID })
                    .then(() => { this.templateDeleted(template) })
            }
        },
    },
}
</script>

<style lang="sass">
@import '~sass/partials/timeline-page-layout.sass'

.template-list-header
    border-bottom: 2px solid $theme-dark-grey
</style>
