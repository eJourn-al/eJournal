<template>
    <div>
        <h3
            class="theme-h3 cursor-pointer unselectable"
            @click="expanded = !expanded"
        >
            Templates
            <icon :name="(expanded) ? 'angle-down' : 'angle-up'"/>
        </h3>

        <div
            v-if="expanded"
            class="d-block"
        >
            <b-card
                :class="$root.getBorderClass($route.params.cID)"
                class="no-hover"
            >
                <div
                    v-if="templates.length > 0"
                    class="menu-list-header"
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
                    class="green-button full-width"
                    :class="{ 'mt-2': templates.length > 0 }"
                    @click="createTemplate()"
                >
                    <icon name="plus"/>
                    Create New Template
                </b-button>

                <b-button
                    class="orange-button mt-2 full-width"
                    @click.stop="importTemplate()"
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
