<template>
    <b-card
        class="journal-card"
        noBody
    >
        <b-card-body>
            <strong
                class="max-one-line"
                :title="template.name"
            >
                <slot class="float-right"/>
                {{ template.name }}
            </strong>

            <entry-preview
                v-if="expanded"
                :template="template"
            />
        </b-card-body>
        <div
            slot="footer"
            class="expand-controls full-width text-center cursor-pointer"
            @click.prevent.stop="expanded = !expanded"
        >
            <icon
                :name="expanded ? 'caret-up' : 'caret-down'"
                class="fill-grey"
            />
        </div>
    </b-card>
</template>

<script>

import EntryPreview from '@/components/entry/EntryPreview.vue'

export default {
    components: {
        EntryPreview,
    },
    props: {
        template: {
            required: true,
        },
    },
    data () {
        return {
            expanded: false,
        }
    },
}
</script>

<style lang="sass">
.journal-card
    .portrait-wrapper
        position: relative
        min-width: 60px
        height: 45px
        img
            border: 1px solid $border-color
            width: 45px
            height: 45px
            border-radius: 50% !important
    .student-details
        position: relative
        width: calc(100% - 60px)
        min-height: 45px
        flex-direction: column
        padding-left: 20px
        .max-one-line
            display: block
            width: 100%
            text-overflow: ellipsis
            white-space: nowrap
            overflow: hidden
        &.list-view
            padding-left: 40px
        @include sm-max
            align-items: flex-end
    .default-cursor
        cursor: default
    .expand-controls
        position: absolute
        bottom: 0px
        left: 0px
</style>
