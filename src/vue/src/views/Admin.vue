<template>
    <content-single-column v-if="instance">
        <bread-crumb/>
        <b-form @submit.prevent="save">
            <h4 class="theme-h4">
                <span>Instance variables</span>
            </h4>
            <b-card
                class="no-hover multi-form"
            >
                <h2 class="theme-h2 field-heading multi-form">
                    Display name
                </h2>
                <b-input
                    v-model="instance.name"
                    class="theme-input multi-form"
                    type="text"
                    placeholder="Name"
                />
                <h2 class="theme-h2 field-heading multi-form">
                    Allow registration
                    <!-- TODO LTI: better excplain this setting with tooltip -->
                    <!-- TODO LTI: add toggle switch after merge with new notifications for nicer switch -->
                </h2>
                <b-button
                    class="add-button float-right"
                    type="submit"
                >
                    <icon name="save"/>
                    Save
                </b-button>
            </b-card>
            <h4 class="theme-h4">
                <span>LTI variables</span>
            </h4>
            <b-card
                class="no-hover multi-form"
            >
                <h2 class="theme-h2 field-heading multi-form">
                    LMS
                </h2>
                <b-form-select
                    v-model="instance.lms_name"
                    :options="lmsNames"
                    :selectSize="1"
                    class="theme-select multi-form mr-2"
                />
                <template v-if="instance.lms_name">
                    <template v-if="instance.lms_url">
                        <h2 class="theme-h2 field-heading multi-form">
                            Configure the tool with the following configuration ({{ configuredToolStep + 1 }} / 4)
                        </h2>

                        <template v-if="configuredToolStep === 0">
                            First, isert the url of the LMS below (e.g. https://canvas.uva.nl/).
                            <h2 class="theme-h2 field-heading multi-form">
                                LMS url
                            </h2>
                            <b-input
                                v-model="instance.lms_url"
                                class="theme-input multi-form"
                                type="text"
                                placeholder="LMS url"
                            />
                        </template>
                        <template v-if="configuredToolStep === 1">
                            Now start adding an LTI Development Key as shown in the screenshot below.
                            <img
                                src="/guide/lti/canvas-connect-1.png"
                                class="theme-img"
                            />
                        </template>
                        <template v-if="configuredToolStep === 2">
                            Fill the fields in as follows:
                            <ul>
                                <li>
                                    Key Name: "eJournal"
                                </li>
                                <li>
                                    Owner Email: "admin@ejournal.app"
                                </li>
                                <li>
                                    Method: "Entry URL"
                                </li>
                                <li>
                                    JSON URL: "{{ configureUrl }}"
                                </li>
                                <li>
                                    Redirect URIs: "{{ launchUrl }}"
                                </li>
                            </ul>
                            An example of this is shown in the screenshot below.
                            <img
                                src="/guide/lti/canvas-connect-2.png"
                                class="theme-img"
                            />
                        </template>
                        <template v-if="configuredToolStep === maxSteps">
                            Now report back the Client ID and Deployment ID in the fields below. If there are multiple
                            deployment IDs, they can be comma seperated.
                            <h2 class="theme-h2 field-heading multi-form">
                                Client ID
                            </h2>
                            <b-input
                                v-model="instance.lti_client_id"
                                class="theme-input multi-form"
                                type="text"
                                placeholder="Client ID (e.g. 10000000000001)"
                            />
                            <h2 class="theme-h2 field-heading multi-form">
                                Deployment IDs
                            </h2>
                            <b-input
                                v-model="instance.lti_deployment_ids"
                                class="theme-input multi-form"
                                type="text"
                                placeholder="Deployment IDs (e.g 1:b21...2gd)"
                            />
                        </template>

                        <b-button
                            v-if="configuredToolStep === maxSteps"
                            class="add-button float-right multi-form"
                            type="submit"
                        >
                            <icon name="save"/>
                            Save
                        </b-button>
                        <b-button
                            v-show="configuredToolStep > 0"
                            class="mr-2 change-button multi-form"
                            @click="configuredToolStep --"
                        >
                            <icon name="arrow-left"/>
                            Previous
                        </b-button>
                        <b-button
                            v-show="configuredToolStep < maxSteps"
                            class="add-button multi-form"
                            @click="configuredToolStep ++"
                        >
                            <icon name="arrow-right"/>
                            Next
                        </b-button>
                    </template>
                </template>
            </b-card>
            <template v-if="instance.lms_name == 'Canvas'">
                <h4 class="theme-h4">
                    <span>Canvas API variables</span>
                </h4>
                <b-card
                    class="no-hover multi-form"
                >
                    <h2 class="theme-h2 field-heading multi-form">
                        Required scopes
                    </h2>
                    <p>
                        Automated user synchronization requires the following scopes:
                        <ul>
                            <li>
                                url:GET|/api/v1/courses/:course_id/sections
                            </li>
                            <li>
                                url:GET|/api/v1/courses/:course_id/users
                            </li>
                        </ul>
                    </p>
                    <h2 class="theme-h2 field-heading multi-form">
                        Client ID
                    </h2>
                    <b-input
                        v-model="instance.api_client_id"
                        class="theme-input multi-form"
                        type="text"
                        placeholder="Client ID"
                    />
                    <h2 class="theme-h2 field-heading multi-form">
                        Client secret
                    </h2>
                    <b-input
                        v-model="instance.api_client_secret"
                        class="theme-input multi-form"
                        type="text"
                        placeholder="Client secret"
                    />
                    <b-button
                        class="add-button float-right"
                        type="submit"
                    >
                        <icon name="save"/>
                        Save
                    </b-button>
                </b-card>
            </template>
        </b-form>
        <custom-footer/>
    </content-single-column>
</template>

<script>
import contentSingleColumn from '@/components/columns/ContentSingleColumn.vue'
import customFooter from '@/components/assets/Footer.vue'
import breadCrumb from '@/components/assets/BreadCrumb.vue'
import instanceAPI from '@/api/instance.js'

export default {
    name: 'Admin',
    components: {
        contentSingleColumn,
        customFooter,
        breadCrumb,
    },
    data () {
        return {
            instance: null,
            configuredToolStep: 0,
            maxSteps: 3,
            lmsNames: [
                { value: null, text: 'No LMS' },
                { value: 'Canvas', text: 'Canvas' },
            ],
        }
    },
    computed: {
        configureUrl () {
            return `${CustomEnv.API_URL}/lti/configure/`
        },
        launchUrl () {
            return `${CustomEnv.API_URL}/lti/launch/`
        },
    },
    watch: {
        instance () {
            if (this.instance.lti_client_id !== null) {
                this.configuredToolStep = this.maxSteps
            }
        },
    },
    created () {
        instanceAPI.get().then((instance) => { this.instance = instance })
    },
    methods: {
        save () {
            instanceAPI.update(this.instance, { customSuccessToast: 'Updated settings' })
                .then((instance) => { this.instance = instance })
        },
    },
}
</script>
