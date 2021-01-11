<template>
    <div v-if="$store.getters['category/assignmentCategories'].length">
        <h2 class="theme-h2 field-heading">
            Categories
        </h2>

        <category-select
            v-if="editable"
            v-model="entry.categories"
            :class="{ 'multi-form': create || edit }"
            :options="$store.getters['category/assignmentCategories']"
            :placeholder="`${(edit && entry.categories.length) ? 'Edit' : 'Add'} categories`"
            @remove="removeCategory"
            @select="addCategory"
        />
        <category-display
            v-if="!editable && 'categories' in entry"
            :id="`${id}-display`"
            :editable="editable"
            :categories="entry.categories"
            @remove-category="removeCategory($event)"
        />
    </div>
</template>

<script>
import CategoryDisplay from '@/components/category/CategoryDisplay.vue'
import CategorySelect from '@/components/category/CategorySelect.vue'

export default {
    name: 'CategoryEdit',
    components: {
        CategoryDisplay,
        CategorySelect,
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
