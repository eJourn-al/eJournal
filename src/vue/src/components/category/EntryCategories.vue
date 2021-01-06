<template>
    <div v-if="$store.getters['category/assignmentCategories'].length">
        <h2
            v-if="create"
            class="theme-h2 field-heading"
        >
            Categories
        </h2>

        <category-display
            v-if="'categories' in entry"
            :id="`${id}-display`"
            :editable="editable"
            :categories="entry.categories"
            @remove-category="removeCategory($event)"
        >
            <b-badge
                v-if="editable"
                v-b-modal="'edit-entry-categories'"
                pill
            >
                Add
                <icon
                    class="fill-green ml-1"
                    name="plus"
                />
            </b-badge>
        </category-display>

        <b-modal
            id="edit-entry-categories"
            size="lg"
            title="Edit entry categories"
            hideFooter
            noEnforceFocus
        >
            <b-card
                class="no-hover no-left-border"
            >
                <h2 class="theme-h2 multi-form">
                    Add or remove any categories from the entry
                </h2>

                <theme-select
                    v-model="entry.categories"
                    label="name"
                    trackBy="id"
                    :options="$store.getters['category/assignmentCategories']"
                    :multiple="true"
                    :searchable="true"
                    :multiSelectText="`${entry.categories && entry.categories.length > 1 ? 'categories' : 'category'}`"
                    placeholder="Search and add or remove categories"
                    @remove="removeCategory"
                    @select="addCategory"
                />
            </b-card>
        </b-modal>
    </div>
</template>

<script>
import CategoryDisplay from '@/components/category/CategoryDisplay'

export default {
    name: 'CategoryEdit',
    components: {
        CategoryDisplay,
    },
    props: {
        entry: {
            required: true,
            type: Object,
        },
        template: {
            required: true,
            type: Object,
        },
        edit: {
            default: false,
            type: Boolean,
        },
        create: {
            default: false,
            type: Boolean,
        },
        id: {
            type: String,
            required: true,
        },
        autosave: {
            type: Boolean,
            default: true,
        },
    },
    computed: {
        editable () {
            return this.$hasPermission('can_grade') || ((this.edit || this.create) && !this.template.fixed_categories)
        },
    },
    created () {
        if (this.create || !('categories' in this.entry)) {
            this.$set(this.entry, 'categories', JSON.parse(JSON.stringify(this.template.categories)))
        }
    },
    methods: {
        removeCategory (category) {
            if (this.create || !this.autosave) {
                this.entry.categories = this.entry.categories.filter(elem => elem.id !== category.id)
            } else {
                this.$store.dispatch(
                    'category/editEntry',
                    { id: category.id, data: { entry_id: this.entry.id, add: false } },
                )
                    .then(() => {
                        this.entry.categories = this.entry.categories.filter(elem => elem.id !== category.id)
                    })
            }
        },
        addCategory (category) {
            if (!this.create && this.autosave) {
                this.$store.dispatch(
                    'category/editEntry',
                    { id: category.id, data: { entry_id: this.entry.id, add: true } },
                )
            }
        },
    },
}
</script>
