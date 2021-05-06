<template>
    <b-card noBody>
        <div
            slot="header"
            class="cursor-pointer "
            @click="expanded = !expanded"
        >
            <h3 class="theme-h3 unselectable">
                Rubrics
            </h3>
            <icon
                :name="(expanded) ? 'angle-down' : 'angle-up'"
                class="float-right fill-grey mt-1 mr-1"
            />
        </div>
        <template v-if="expanded">
            <rubric-menu-item
                v-for="rubric in rubrics"
                :key="`rubric-${rubric.id}-menu-item`"
                :rubric="rubric"
                @delete-rubric="deleteRubric($event)"
                @select-rubric="selectRubric({ rubric: $event })"
            />

            <b-card-body
                class="d-block p-2"
            >
                <b-button
                    variant="link"
                    class="green-button"
                    @click="createRubric()"
                >
                    <icon name="plus"/>
                    Create New Rubric
                </b-button>

                <b-button
                    variant="link"
                    class="orange-button"
                    @click.stop="importRubric()"
                >
                    <icon name="file-import"/>
                    Import Rubric
                </b-button>
            </b-card-body>
        </template>
    </b-card>
</template>

<script>
import RubricMenuItem from '@/components/rubric/RubricMenuItem.vue'

import { mapActions, mapGetters, mapMutations } from 'vuex'

export default {
    name: 'TemplateMenu',
    components: {
        RubricMenuItem,
    },
    data () {
        return {
            expanded: true,
        }
    },
    computed: {
        ...mapGetters({
            rubrics: 'rubric/assignmentRubrics',
        }),
    },
    methods: {
        ...mapMutations({
            selectRubric: 'assignmentEditor/SELECT_RUBRIC',
            createRubric: 'assignmentEditor/CREATE_RUBRIC',
            importRubric: 'assignmentEditor/SET_ACTIVE_COMPONENT_TO_RUBRIC_IMPORT',
        }),
        ...mapActions({
            rubricDelete: 'rubric/delete',
            rubricDeleted: 'assignmentEditor/rubricDeleted',
        }),
        deleteRubric (rubric) {
            if (window.confirm(
                `Are you sure you want to delete rubric "${rubric.name}" from this assignment?`)) {
                this.rubricDelete({ id: rubric.id, aID: this.$route.params.aID })
                    .then(() => { this.rubricDeleted({ rubric }) })
            }
        },
    },
}
</script>
