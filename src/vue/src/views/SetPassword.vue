<template>
    <content-single-column class="not-logged-in-page">
        <img
            class="not-logged-in-page-logo"
            src="/ejournal-logo.svg"
        />
        <b-card>
            <h2
                slot="header"
                class="theme-h2"
            >
                {{ title }}
            </h2>
            {{ instructions }}

            <b-form
                id="setPasswordForm"
                class="mt-2"
                @submit.prevent="setPassword"
            >
                <b-form-input
                    v-model="username"
                    name="username"
                    autocomplete="username"
                    hidden
                />

                <b-form-group required>
                    <template #label>
                        New password
                        <tooltip tip="Should contain at least 8 characters, a capital letter and a special character"/>
                    </template>

                    <b-form-input
                        v-model="password"
                        type="password"
                        required
                        placeholder="New password"
                        autocomplete="new-password"
                    />
                </b-form-group>

                <b-form-group
                    label="Repeat new password"
                    required
                >
                    <b-input
                        v-model="passwordRepeated"
                        type="password"
                        required
                        placeholder="Repeat new password"
                        autocomplete="new-password"
                    />
                </b-form-group>
            </b-form>

            <b-button
                slot="footer"
                class="float-right green-button"
                type="submit"
                form="setPasswordForm"
            >
                <icon name="save"/>
                Save
            </b-button>
        </b-card>

        <custom-footer/>
    </content-single-column>
</template>

<script>
import contentSingleColumn from '@/components/columns/ContentSingleColumn.vue'
import customFooter from '@/components/assets/Footer.vue'
import tooltip from '@/components/assets/Tooltip.vue'

import authAPI from '@/api/auth.js'
import validation from '@/utils/validation.js'

import { mapGetters } from 'vuex'

export default {
    name: 'SetPassword',
    components: {
        contentSingleColumn,
        customFooter,
        tooltip,
    },
    props: ['username', 'token'],
    data () {
        return {
            password: '',
            passwordRepeated: '',
        }
    },
    computed: {
        ...mapGetters({
            instanceName: 'instance/name',
        }),
        title () {
            if (this.$route.query.new_user) {
                return 'Complete registration'
            }
            return 'Password recovery'
        },
        instructions () {
            if (this.$route.query.new_user) {
                return `To complete your registration at ${this.instanceName}, please set a password below.`
            }
            return `To continue using ${this.instanceName}, please set a new password below.`
        },
    },
    methods: {
        setPassword () {
            if (validation.validatePassword(this.password, this.passwordRepeated)) {
                authAPI.setPassword(
                    this.username,
                    this.token,
                    this.password,
                    { responseSuccessToast: true },
                )
                    .then(() => {
                        this.$store.dispatch('user/logout')
                        this.$router.push({ name: 'Login' })
                    })
            }
        },
    },
}
</script>
