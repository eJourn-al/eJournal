<template>
    <div>
        <h2 class="theme-h2 field-heading">
            Name
        </h2>
        The name of your institution. This name appears in invitation emails as well as on the login page.
        <div class="d-flex mb-2">
            <b-input
                v-model="instance.name"
                class="theme-input mr-2 mb-2"
                type="text"
            />
            <b-button
                type="submit"
                class="green-button mb-2"
                :class="{ 'input-disabled': saveRequestInFlight }"
                @click="saveChanges({ name: instance.name })"
            >
                <icon name="save"/>
                Save
            </b-button>
        </div>
        <radio-button
            v-model="instance.allow_standalone_registration"
            :options="[
                {
                    value: true,
                    icon: 'check',
                    class: 'green-button',
                },
                {
                    value: false,
                    icon: 'times',
                    class: 'red-button',
                },
            ]"
            class="float-right mb-2 ml-2"
            @input="saveChanges({ allow_standalone_registration: instance.allow_standalone_registration })"
        />
        <h2 class="theme-h2 field-heading">
            Self sign-up
        </h2>
        Allow users to self sign-up for eJournal.
    </div>
</template>

<script>
import RadioButton from '@/components/assets/RadioButton.vue'

import instanceAPI from '@/api/instance.js'

export default {
    components: {
        RadioButton,
    },
    data () {
        return {
            instance: {
                name: '',
                allow_standalone_registration: true,
            },
            saveRequestInFlight: false,
        }
    },
    created () {
        instanceAPI.get()
            .then((instance) => {
                this.instance = instance
            })
    },
    methods: {
        saveChanges (changes) {
            this.saveRequestInFlight = true
            instanceAPI.update(changes, {
                customSuccessToast: 'Successfully updated instance details.',
            })
                .finally(() => {
                    this.saveRequestInFlight = false
                })
        },
    },
}
</script>
