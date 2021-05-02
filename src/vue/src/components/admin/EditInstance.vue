<template>
    <load-wrapper :loading="!instance">
        <b-form
            v-if="instance"
            @submit="submitForm"
        >
            <b-form-group
                label="Name"
                description="
                    The name of your institution.
                    This name appears in invitation emails as well as on the login page.
                "
            >
                <b-form-input
                    v-model="instance.name"
                    class="theme-input mr-2 mb-2"
                    type="text"
                    required
                />
            </b-form-group>

            <b-form-group
                label="Kaltura url"
                description="URL to your Kaltura domain. Used to instruct users when uploading a video."
            >
                <b-form-input
                    v-model="instance.kaltura_url"
                    class="theme-input mb-2"
                    type="url"
                />
            </b-form-group>

            <b-form-group
                label="Self sign-up"
                description="Allow users to self sign-up for eJournal."
            >
                <b-form-radio-group
                    v-model="instance.allow_standalone_registration"
                    class="theme-boolean-radio"
                    :options="[
                        {
                            value: true,
                            text: 'Yes',
                        },
                        {
                            value: false,
                            text: 'No',
                        },
                    ]"
                    name="radios-btn-default"
                    buttons
                />
            </b-form-group>

            <b-button
                type="submit"
                class="green-button float-right mb-2"
                :class="{ 'input-disabled': saveRequestInFlight }"
            >
                <icon name="save"/>
                Save
            </b-button>
        </b-form>
    </load-wrapper>
</template>

<script>
import LoadWrapper from '@/components/loading/LoadWrapper.vue'

import { mapActions, mapGetters } from 'vuex'

export default {
    components: {
        LoadWrapper,
    },
    data () {
        return {
            saveRequestInFlight: false,
            dirty: false,
        }
    },
    computed: {
        ...mapGetters({
            getInstance: 'instance/instance',
        }),
        instance () { return this.getInstance },
    },
    watch: {
        instance: {
            deep: true,
            handler (val, oldVal) {
                if (oldVal) {
                    this.dirty = true
                }
            },
        },
        dirty () { this.$emit('dirty-changed', this.dirty) },
    },
    methods: {
        ...mapActions({
            update: 'instance/update',
        }),
        submitForm (event) {
            event.preventDefault()
            this.saveRequestInFlight = true

            this.update({
                data: this.instance,
                connArgs: { customSuccessToast: 'Successfully updated instance details.' },
            })
                .finally(() => {
                    this.saveRequestInFlight = false
                    this.dirty = false
                })
        },
    },
}
</script>

<style lang="sass">
.theme-boolean-radio > .btn.btn-secondary.active
    background-color: $theme-blue !important
</style>
