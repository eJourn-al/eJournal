<template>
    <div v-if="templates.length > 1">
        <template-card
            v-for="template in templates"
            :key="template.id"
            :template="template"
        >
            <b-button
                class="green-button float-right"
                variant="link"
                @click="$emit('select-template', template.id)"
            >
                <icon name="user-plus"/>
                Select
            </b-button>
        </template-card>
    </div>
    <load-spinner v-else/>
</template>

<script>
import TemplateCard from '@/components/template/TemplateCard.vue'
import loadSpinner from '@/components/loading/LoadSpinner.vue'

export default {
    components: {
        TemplateCard,
        loadSpinner,
    },
    props: {
        templates: {
            required: true,
        },
    },
}
</script>
