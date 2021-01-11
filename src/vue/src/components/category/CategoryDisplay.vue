<template>
    <div>
        <category-tag
            v-for="category in categories"
            :key="`${id}-category-${category.id}`"
            :category="category"
            :removable="editable"
            :showInfo="true"
            @select-category="$emit('select-category', category)"
            @remove-category="$emit('remove-category', category)"
            @show-info="
                infoCategory = $event
                $nextTick(() => { $bvModal.show(infoModalID) })
            "
        />

        <slot/>

        <category-information-modal
            :id="infoModalID"
            :category="infoCategory"
        />
    </div>
</template>

<script>
import CategoryInformationModal from '@/components/category/CategoryInformationModal.vue'
import CategoryTag from '@/components/category/CategoryTag.vue'

export default {
    name: 'CategoryDisplay',
    components: {
        CategoryInformationModal,
        CategoryTag,
    },
    props: {
        categories: {
            required: true,
            type: Array,
        },
        id: {
            type: String,
            required: true,
        },
        editable: {
            default: false,
        },
    },
    data () {
        return {
            infoCategory: null,
        }
    },
    computed: {
        infoModalID () { return `${this.id}-category-information` },
    },
}
</script>
