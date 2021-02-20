<template>
    <div>
        <progress-node
            v-if="presetNode && presetNode.type === 'p'"
            :class="$root.getBorderClass($route.params.cID)"
            :currentNode="presetNode"
            :nodes="presetNodes"
            :bonusPoints="0"
        >
            <template #edit-button>
                <b-button
                    class="ml-auto orange-button"
                    @click.stop="setModeToEdit()"
                >
                    <icon name="edit"/>
                    Edit
                </b-button>
            </template>
        </progress-node>

        <b-card
            v-else-if="presetNode && presetNode.type === 'd'"
            :class="$root.getBorderClass($route.params.cID)"
            class="no-hover"
        >
            <entry-preview
                :presetNode="presetNode"
                :template="template"
            >
                <template #edit-button>
                    <b-button
                        class="ml-auto orange-button"
                        @click.stop="setModeToEdit()"
                    >
                        <icon name="edit"/>
                        Edit
                    </b-button>
                </template>
            </entry-preview>
        </b-card>
    </div>
</template>

<script>
import EntryPreview from '@/components/entry/EntryPreview.vue'
import ProgressNode from '@/components/entry/ProgressNode.vue'

import { mapGetters, mapMutations } from 'vuex'

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
        ...mapMutations({
            setModeToEdit: 'assignmentEditor/SET_ACTIVE_COMPONENT_MODE_TO_EDIT',
        }),
    },
}
</script>
