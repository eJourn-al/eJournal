<template>
    <div>
        <progress-node
            v-if="presetNode && presetNode.type === 'p'"
            :currentNode="presetNode"
            :nodes="presetNodes"
            :bonusPoints="0"
        >
            <b-button
                slot="edit-button"
                class="float-right grey-button ml-2"
                @click.stop="setModeToEdit()"
            >
                <icon name="edit"/>
                Edit
            </b-button>
            <b-button
                slot="edit-button"
                class="red-button float-right"
                @click.stop="deletePresetNode()"
            >
                <icon name="trash"/>
                Delete
            </b-button>
        </progress-node>

        <b-card v-else-if="presetNode && presetNode.type === 'd'">
            <template #header>
                <b-button
                    class="float-right ml-2 grey-button"
                    @click.stop="setModeToEdit()"
                >
                    <icon name="edit"/>
                    Edit
                </b-button>
                <b-button
                    slot="edit-button"
                    class="red-button float-right"
                    @click.stop="deletePresetNode()"
                >
                    <icon name="trash"/>
                    Delete
                </b-button>
                <h2 class="theme-h2">
                    {{ presetNode.display_name }}
                </h2>
            </template>
            <entry-preview
                :presetNode="presetNode"
                :template="template"
            />
        </b-card>
    </div>
</template>

<script>
import EntryPreview from '@/components/entry/EntryPreview.vue'
import ProgressNode from '@/components/entry/ProgressNode.vue'

import { mapActions, mapGetters, mapMutations } from 'vuex'

export default {
    components: {
        EntryPreview,
        ProgressNode,
    },
    computed: {
        ...mapGetters({
            presetNodes: 'presetNode/assignmentPresetNodes',
            presetNode: 'assignmentEditor/selectedPresetNode',
            templates: 'template/assignmentTemplates',
        }),
        /* Do not use the presetNode serialized template as it might be stale due to updates else where */
        template () {
            return this.templates.find((elem) => elem.id === this.presetNode.template.id)
        },
    },
    methods: {
        ...mapActions({
            delete: 'presetNode/delete',
            presetNodeDeleted: 'assignmentEditor/presetNodeDeleted',
        }),
        ...mapMutations({
            setModeToEdit: 'assignmentEditor/SET_ACTIVE_COMPONENT_MODE_TO_EDIT',
        }),
        deletePresetNode () {
            if (window.confirm(
                `Are you sure you want to remove '${this.presetNode.display_name}' from the assignment?`)) {
                this.delete({ id: this.presetNode.id, aID: this.$route.params.aID })
                    .then(() => { this.presetNodeDeleted({ presetNode: this.presetNode }) })
            }
        },
    },
}
</script>
