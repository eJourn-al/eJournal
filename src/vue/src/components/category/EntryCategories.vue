<template>
    <div
        v-if="($store.getters['category/assignmentCategories'].length
            && (editable || entry.categories)) || (displayOnly && template.categories.length > 0)"
        class="p-2 background-light-grey round-border d-inline-block"
        :class="{ 'full-width': editMode, }"
    >
        <b>Categories</b>
        <span
            v-if="editable && !editMode"
            class="text-grey cursor-pointer small"
            @click="editMode = true"
        >
            Edit
        </span><br/>

        <category-display
            v-if="(!editMode && 'categories' in entry) || displayOnly"
            :id="`${id}-display`"
            :editable="editable"
            :categories="displayOnly ? template.categories : entry.categories"
            class="small"
            @remove-category="removeCategory($event)"
        />

        <category-select
            v-else-if="editable"
            v-model="entry.categories"
            :options="$store.getters['category/assignmentCategories']"
            :placeholder="`${(edit && entry.categories.length) ? 'Edit' : 'Add'} categories`"
            :startOpen="editMode"
            :openDirection="'top'"
            @remove="removeCategory"
            @select="addCategory"
            @close="editMode = false"
        />

        <i
            v-if="!editMode && 'categories' in entry && entry.categories.length === 0"
            class="text-grey small"
        >
            This entry has no categories.
        </i>
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
        displayOnly: {
            type: Boolean,
            default: false,
        },
    },
    data () {
        return {
            editMode: false,
        }
    },
    computed: {
        editable () {
            return (
                !this.displayOnly
                && (
                    this.$hasPermission('can_grade')
                    || (
                        (this.edit || this.create)
                        && this.template.allow_custom_categories
                    )
                )
            )
        },
    },
    created () {
        if ((this.create || !('categories' in this.entry)) && !this.displayOnly) {
            this.$set(this.entry, 'categories', JSON.parse(JSON.stringify(this.template.categories)))
        }
    },
    methods: {
        removeCategory (category) {
            if (this.create || !this.autosave) {
                this.entry.categories = this.entry.categories.filter((elem) => elem.id !== category.id)
            } else {
                this.$store.dispatch(
                    'category/editEntry',
                    { id: category.id, data: { entry_id: this.entry.id, add: false } },
                )
                    .then(() => {
                        this.entry.categories = this.entry.categories.filter((elem) => elem.id !== category.id)
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
