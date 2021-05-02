<template>
    <b-card noBody>
        <div
            slot="header"
            class="cursor-pointer "
            @click="expanded = !expanded"
        >
            <h3 class="theme-h3 unselectable">
                Templates
            </h3>
            <icon
                :name="(expanded) ? 'angle-down' : 'angle-up'"
                class="float-right fill-grey mt-1 mr-1"
            />
        </div>
        <template v-if="expanded">
            <template-menu-item
                v-for="template in templates"
                :key="`template-${template.id}-menu-item`"
                :template="template"
                @delete-template="deleteTemplate($event)"
                @select-template="selectTemplate({ template: $event })"
            />

            <b-card-body
                class="d-block p-2"
            >
                <b-button
                    variant="link"
                    class="green-button"
                    @click="createTemplate({ fromPresetNode: false })"
                >
                    <icon name="plus"/>
                    Create New Template
                </b-button>

                <b-button
                    variant="link"
                    class="orange-button"
                    @click.stop="importTemplate()"
                >
                    <icon name="file-import"/>
                    Import Template
                </b-button>
            </b-card-body>
        </template>
    </b-card>
</template>

<script>
import TemplateMenuItem from '@/components/template/TemplateMenuItem.vue'

import { mapActions, mapGetters, mapMutations } from 'vuex'

export default {
    name: 'TemplateMenu',
    components: {
        TemplateMenuItem,
    },
    data () {
        return {
            expanded: true,
        }
    },
    computed: {
        ...mapGetters({
            templates: 'template/assignmentTemplates',
        }),
    },
    methods: {
        ...mapMutations({
            selectTemplate: 'assignmentEditor/SELECT_TEMPLATE',
            createTemplate: 'assignmentEditor/CREATE_TEMPLATE',
            importTemplate: 'assignmentEditor/SET_ACTIVE_COMPONENT_TO_TEMPLATE_IMPORT',
        }),
        ...mapActions({
            templateDelete: 'template/delete',
            templateDeleted: 'assignmentEditor/templateDeleted',
        }),
        deleteTemplate (template) {
            if (window.confirm(
                `Are you sure you want to delete template "${template.name}" from this assignment?`)) {
                this.templateDelete({ id: template.id, aID: this.$route.params.aID })
                    .then(() => { this.templateDeleted({ template }) })
            }
        },
    },
}
</script>
