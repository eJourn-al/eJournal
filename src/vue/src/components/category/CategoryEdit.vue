<template>
    <div>
        <b-form-group
            label="Name"
            :invalid-feedback="nameInvalidFeedback"
        >
            <b-form-input
                v-model="data.name"
                :state="nameInputState"
                autofocus
                placeholder="Name"
                class="theme-input"
                type="text"
                trim
            />
        </b-form-group>

        <b-form-group label="Description">
            <text-editor
                :id="descriptionTextEditorID"
                :key="descriptionTextEditorID"
                ref="descriptionTextEditor"
                v-model="data.description"
                :footer="false"
                :basic="true"
                placeholder="Description"
                @editor-focus="descriptionFocused = true"
                @editor-blur="descriptionFocused = false"
            />
        </b-form-group>

        <b-form-group label="Templates">
            <theme-select
                v-model="data.templates"
                label="name"
                trackBy="id"
                :options="templates"
                :multiple="true"
                :focus="descriptionFocused"
                :searchable="true"
                :multiSelectText="`template${data.templates.length > 1 ? 's' : ''}`"
                placeholder="Search and add or remove templates"
            />
        </b-form-group>

        <b-form-group
            label="Color"
            :invalid-feedback="colorInvalidFeedback"
        >
            <b-input
                v-model="data.color"
                :state="colorInputState"
                type="color"
            />
        </b-form-group>
    </div>
</template>

<script>
import { mapGetters } from 'vuex'

export default {
    name: 'CategoryEdit',
    components: {
        textEditor: () => import(/* webpackChunkName: 'text-editor' */ '@/components/assets/TextEditor.vue'),
    },
    props: {
        data: {
            required: true,
            type: Object,
        },
        templates: {
            required: true,
            type: Array,
        },
    },
    data () {
        return {
            updateCall: null,
            createCall: null,
            descriptionFocused: false,
            nameInvalidFeedback: null,
            colorInvalidFeedback: null,
            aID: null,
        }
    },
    computed: {
        ...mapGetters({
            categories: 'category/assignmentCategories',
        }),
        descriptionTextEditorID () { return `text-editor-category-${this.data.id}-description` },
        validCategory () {
            return (
                this.nameInputState !== false
                && this.colorInputState !== false
            )
        },
        nameInputState () {
            if (this.data.name === '') {
                this.nameInvalidFeedback = 'Name cannot be empty' // eslint-disable-line
                return false
            }
            if (this.categories.some(cat => cat.id !== this.data.id && cat.name === this.data.name)) {
                this.nameInvalidFeedback = 'Name is not unique' // eslint-disable-line
                return false
            }

            this.nameInvalidFeedback = null // eslint-disable-line
            return null
        },
        colorInputState () {
            if (this.categories.some(cat => cat.id !== this.data.id && cat.color === this.data.color)) {
                this.colorInvalidFeedback = 'Color is not unique' // eslint-disable-line
                return false
            }

            this.colorInvalidFeedback = null // eslint-disable-line
            return null
        },
    },
    watch: {
        data: {
            deep: true,
            handler (category) {
                if (category.id >= 0) {
                    this.patchCategory(category)
                } else {
                    this.createCategory(category)
                }
            },
        },
    },
    created () {
        this.aID = this.$route.params.aID
    },
    methods: {
        patchCategory (data) {
            window.clearTimeout(this.updateCall)

            if (!this.validCategory) { return }

            const payload = JSON.parse(JSON.stringify(data))
            payload.templates = data.templates.map(elem => elem.id)

            this.updateCall = window.setTimeout(() => {
                this.$store.dispatch('category/update', { id: payload.id, data: payload })
            }, 3000)
        },
        createCategory (localCategory) {
            window.clearTimeout(this.createCall)

            if (!this.validCategory) { return }

            this.createCall = window.setTimeout(() => {
                this.$store.dispatch('category/createAndOnlyUpdateId', { localCategory, aID: this.aID })
            }, 3000)
        },
    },
}
</script>
