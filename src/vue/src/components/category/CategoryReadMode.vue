<template>
    <div>
        <b-form-group>
            <template #label>
                Category
                <tooltip tip="This is how the category is displayed for most users"/>
            </template>

            <category-display
                v-if="category.name"
                :id="`category-${category.id}-display`"
                :editable="false"
                :categories="[category]"
            />
            <span
                v-else
                class="no-optional-content-value"
            >
                No name provided.
            </span>
        </b-form-group>

        <b-form-group label="Description">
            <sandboxed-iframe
                v-if="category.description"
                :content="category.description"
            />
            <span
                v-else
                class="no-optional-content-value"
            >
                No description provided.
            </span>
        </b-form-group>

        <b-form-group label="Templates">
            <b-badge
                v-for="template in category.templates"
                :key="`category-${category.id}-template-${template.id}-display`"
                class="mr-1"
                pill
            >
                {{ template.name }}
            </b-badge>
            <span
                v-if="!category.templates.length"
                class="no-optional-content-value"
            >
                No templates have this category set as part of their (fixed) default categories.
            </span>
        </b-form-group>
    </div>
</template>

<script>
import CategoryDisplay from '@/components/category/CategoryDisplay.vue'
import SandboxedIframe from '@/components/assets/SandboxedIframe.vue'
import Tooltip from '@/components/assets/Tooltip.vue'

export default {
    name: 'CategoryReadMode',
    components: {
        CategoryDisplay,
        SandboxedIframe,
        Tooltip,
    },
    props: {
        category: {
            required: true,
            type: Object,
        },
    },
}
</script>
