<template>
    <b-row noGutters>
        <b-col md="6">
            <b-card
                class="select-type mr-md-1 entry-type"
                :class="{
                    'active': presetNode.type === 'd',
                    'unselected': presetNode.type === 'p',
                }"
                @click="presetNode.type = 'd'"
            >
                <template #header>
                    <icon
                        class="mr-2 shift-up-4"
                        name="calendar"
                    />
                    <b>Entry</b>
                </template>
                <div class="unselectable">
                    Requires students to post an entry using a specified template.
                </div>
            </b-card>
        </b-col>

        <b-col md="6">
            <b-card
                class="select-type ml-md-1 progress-type"
                :class="{
                    'active': presetNode.type === 'p',
                    'unselected': presetNode.type === 'd',
                }"
                @click="presetNode.type = 'p'"
            >
                <template #header>
                    <icon
                        class="mr-2 shift-up-4"
                        name="flag-checkered"
                    />
                    <b>Progress goal</b>
                </template>
                <div class="unselectable">
                    Indicates an intermediate point target that should be achieved.
                </div>
            </b-card>
        </b-col>
    </b-row>
</template>

<script>
export default {
    props: {
        presetNode: {
            required: true,
            type: Object,
        },
    },
}
</script>

<style lang="sass" scoped>
.card.select-type
    &.unselected
        opacity: 0.6
    &.active, &:hover
        opacity: 1
        &.entry-type .card-header
            background-color: $theme-blue
        &.progress-type .card-header
            background-color: $theme-yellow
        .card-header
            color: white
    &:not(.active)
        cursor: pointer
        &:hover .card-body
            background-color: $theme-light-grey
</style>
