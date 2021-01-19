<template>
    <b-card
        :class="$root.getBorderClass($route.params.cID)"
        class="no-hover template-card"
    >
        <!-- <h2 class="theme-h2 multi-form">
            {{ `${(edit) ? 'Edit' : 'Create'} Template` }}
        </h2> -->

        <div class="d-flex">
            <b-button
                :class="{'active': mode === activeComponentModeOptions.edit}"
                class="orange-button flex-basis-100"
                @click="setActiveComponentMode(activeComponentModeOptions.edit)"
            >
                <icon name="edit"/>
                Edit
            </b-button>
            <b-button
                :class="{'active': mode === activeComponentModeOptions.read}"
                class="green-button flex-basis-100"
                @click="setActiveComponentMode(activeComponentModeOptions.read)"
            >
                <icon name="eye"/>
                Preview
            </b-button>
        </div>

        <hr/>

        <div v-show="mode === activeComponentModeOptions.edit">
            <b-form-group
                label="Name"
                :invalid-feedback="nameInvalidFeedback"
            >
                <b-input
                    v-model="template.name"
                    placeholder="Name"
                    class="theme-input"
                    type="text"
                    trim
                    required
                    :state="nameInputState"
                />
            </b-form-group>

            <template-edit-settings :template="template"/>

            <hr/>

            <template-edit-fields :template="template"/>

            <hr/>

            <!-- TODO: Make it safe to use categories length to improve placeholder and hide categories when no exist-->
            <b-form-group label="Categories">
                <category-select
                    v-model="template.categories"
                    :options="$store.getters['category/assignmentCategories']"
                    :openDirection="'top'"
                    placeholder="Set categories"
                />
            </b-form-group>

            <b-button
                class="green-button float-right"
                @click="finalizeTemplateChanges"
            >
                <icon :name="(edit) ? 'save' : 'plus'"/>
                {{ `${(edit) ? 'Update' : 'Add'} Template` }}
            </b-button>
        </div>

        <template v-if="mode === activeComponentModeOptions.read">
            <!-- TODO: Add entry title component after merge branch consistent-entry-title -->

            <entry-fields
                :template="template"
                :content="() => Object()"
                :edit="true"
                :readOnly="true"
            />
            <category-display
                :id="`template-${template.id}-preview`"
                :template="template"
                :categories="template.categories"
            />
        </template>
    </b-card>
</template>

<script>
import CategoryDisplay from '@/components/category/CategoryDisplay.vue'
import CategorySelect from '@/components/category/CategorySelect.vue'
import EntryFields from '@/components/entry/EntryFields.vue'
import TemplateEditFields from '@/components/template/TemplateEditFields.vue'
import TemplateEditSettings from '@/components/template/TemplateEditSettings.vue'

import { mapActions, mapGetters, mapMutations } from 'vuex'

export default {
    components: {
        CategoryDisplay,
        CategorySelect,
        EntryFields,
        TemplateEditFields,
        TemplateEditSettings,
    },
    props: {
        template: {
            required: true,
            type: Object,
        },
    },
    data () {
        return {
            nameInvalidFeedback: null,
        }
    },
    computed: {
        ...mapGetters({
            templates: 'template/assignmentTemplates',
            activeComponentModeOptions: 'assignmentEditor/activeComponentModeOptions',
            mode: 'assignmentEditor/activeComponentMode',
        }),
        edit () { return this.template.id >= 0 },
        nameInputState () {
            if (this.template.name === '') {
                this.nameInvalidFeedback = 'Name cannot be empty' // eslint-disable-line
                return false
            }
            if (this.templates.some(elem => elem.id !== this.template.id && elem.name === this.template.name)) {
                this.nameInvalidFeedback = 'Name is not unique' // eslint-disable-line
                return false
            }

            this.nameInvalidFeedback = null // eslint-disable-line
            return null
        },
    },
    methods: {
        ...mapMutations({
            selectTemplate: 'assignmentEditor/selectTemplate',
            setActiveComponent: 'assignmentEditor/setActiveComponent',
            setActiveComponentMode: 'assignmentEditor/setActiveComponentMode',
            setActiveComponentModeToRead: 'assignmentEditor/setActiveComponentModeToRead',
            templateCreated: 'assignmentEditor/templateCreated',
        }),
        ...mapActions({
            create: 'template/create',
            update: 'template/update',
        }),
        finalizeTemplateChanges () {
            if (this.nameInputState === false) {
                this.$toasted.error(this.nameInvalidFeedback)
                return
            }

            if (this.edit) {
                this.update({ id: this.template.id, data: this.template, aID: this.$route.params.aID })
                    .then(() => { this.setActiveComponentModeToRead() })
            } else {
                this.create({ template: this.template, aID: this.$route.params.aID })
                    .then(() => { this.templateCreated() })
            }
        },
    },
}
</script>
