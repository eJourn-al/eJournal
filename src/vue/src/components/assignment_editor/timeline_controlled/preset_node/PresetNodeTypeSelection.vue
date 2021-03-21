<template>
    <b-row noGutters>
        <b-col md="6">
            <b-card
                class="select-type mr-md-1"
                :class="{'unselected': presetNode.type === 'p'}"
                @click="presetNode.type = 'd'"
            >
                <icon
                    class="float-left mr-3 mt-3 mb-4"
                    name="calendar"
                    scale="2"
                />
                <div class="unselectable">
                    <b>Entry</b><br/>
                    A template that should be filled in before a set deadline.
                </div>
            </b-card>
        </b-col>

        <b-col md="6">
            <b-card
                class="select-type ml-md-1"
                :class="{'unselected': presetNode.type === 'd'}"
                @click="presetNode.type = 'p'"
            >
                <icon
                    class="float-left mr-3 mt-3 mb-4"
                    name="flag-checkered"
                    scale="2"
                />
                <div class="unselectable">
                    <b>Progress</b><br/>
                    A point target to indicate required progress.
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
.select-type.unselected, .select-type.unselected:hover
    opacity: 0.5
</style>
