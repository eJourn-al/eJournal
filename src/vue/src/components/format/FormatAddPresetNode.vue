<template>
    <div>
        <b-card
            :class="$root.getBorderClass($route.params.cID)"
            class="no-hover overflow-x-hidden"
        >
            <h2 class="theme-h2 d-inline multi-form">
                New preset
            </h2>
            <h2 class="theme-h2 field-heading required">
                Preset Type
            </h2>
            <b-row>
                <b-col md="6">
                    <b-card
                        :class="{'unselected': currentPreset.type !== '' && currentPreset.type !== 'd'}"
                        @click="currentPreset.type = 'd'"
                    >
                        <b-button
                            :class="{'selected': currentPreset.type === 'd'}"
                            class="change-button preset-type-button float-left mr-3 mt-2 no-hover"
                        >
                            <icon
                                name="calendar"
                                scale="1.8"
                            />
                        </b-button>
                        <div class="unselectable">
                            <b>Entry</b><br/>
                            An entry that should be filled in before a set deadline.
                        </div>
                    </b-card>
                </b-col>
                <b-col md="6">
                    <b-card
                        :class="{'unselected': currentPreset.type !== '' && currentPreset.type !== 'p'}"
                        @click="currentPreset.type = 'p'"
                    >
                        <b-button
                            :class="{'selected': currentPreset.type === 'p'}"
                            class="change-button preset-type-button float-left mr-3 mt-2 no-hover"
                        >
                            <icon
                                name="flag-checkered"
                                scale="1.8"
                            />
                        </b-button>
                        <div class="unselectable">
                            <b>Progress</b><br/>
                            A point target to indicate required progress.
                        </div>
                    </b-card>
                </b-col>
            </b-row>

            <div
                v-if="currentPreset.type !== ''"
                class="mt-2"
            >
                <preset-node-card
                    :newPreset="true"
                    :currentPreset="currentPreset"
                    :templates="templates"
                    :assignmentDetails="assignmentDetails"
                />

                <b-alert
                    :show="showAlert"
                    class="error"
                    dismissible
                    @dismissed="showAlert = false"
                >
                    Some required fields are empty or invalid.
                </b-alert>

                <b-button
                    class="add-button float-right"
                    @click="addPreset"
                >
                    <icon name="plus"/>
                    Add preset
                </b-button>
            </div>
        </b-card>
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
                type: '',
                template: '',
                description: '',
                files: [],
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

            return validTarget && validTemplate && this.currentPreset.due_date
        },
    },
}
</script>
