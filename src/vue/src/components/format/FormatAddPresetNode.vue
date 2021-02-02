<template>
    <div>
        <b-row noGutters>
            <b-col md="6">
                <b-card
                    class="select-type mr-md-1"
                    :class="{'unselected': currentPreset.type === 'p'}"
                    @click="currentPreset.type = 'd'"
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
                    class="select-type border-yellow ml-md-1"
                    :class="{'unselected': currentPreset.type === 'd'}"
                    @click="currentPreset.type = 'p'"
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
        <b-alert
            :show="showAlert"
            class="error"
            dismissible
            @dismissed="showAlert = false"
        >
            Some required fields are empty or invalid.
        </b-alert>
        <preset-node-card
            v-if="currentPreset.type"
            :newPreset="true"
            :currentPreset="currentPreset"
            :templates="templates"
            :assignmentDetails="assignmentDetails"
            @new-template="preset => $emit('new-template', currentPreset)"
            @add-preset="addPreset"
        />
    </div>
</template>

<script>
import formatPresetNodeCard from '@/components/format/FormatPresetNodeCard.vue'

export default {
    components: {
        'preset-node-card': formatPresetNodeCard,
    },
    props: ['templates', 'assignmentDetails'],
    data () {
        return {
            currentPreset: {
                type: null,
                template: '',
                display_name: '',
                description: '',
                attached_files: [],
            },
            showAlert: false,
        }
    },
    methods: {
        addPreset () {
            if (this.validPreset()) {
                if (this.currentPreset.type !== 'p') {
                    this.currentPreset.target = ''
                }
                if (this.currentPreset.type !== 'd') {
                    this.currentPreset.template = null
                    this.currentPreset.unlock_date = null
                    this.currentPreset.lock_date = null
                }

                this.$emit('add-preset', this.currentPreset)
            } else {
                this.showAlert = true
            }
        },
        validPreset () {
            const validTarget = this.currentPreset.target > 0 || this.currentPreset.type === 'd'
            const validTemplate = this.currentPreset.template || this.currentPreset.type === 'p'

            return validTarget && validTemplate && this.currentPreset.due_date && this.currentPreset.display_name
        },
    },
}
</script>
<style lang="sass" scoped>
.select-type.unselected, .select-type.unselected:hover
    opacity: 0.5

</style>
