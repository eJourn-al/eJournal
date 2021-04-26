<template>
    <content-single-column>
        <h1 class="theme-h1">
            <span>{{ title }}</span>
        </h1>
        <b-card class="no-hover">
            <h2 class="theme-h2 multi-form">
                Set a password
            </h2>
            {{ instructions }}
            <b-form
                class="mt-2"
                @submit.prevent="setPassword"
            >
                <h2 class="theme-h2 field-heading">
                    New password
                    <tooltip
                        tip="Should contain at least 8 characters, a capital letter and a special character"
                    />
                </h2>
                <b-input
                    v-model="password"
                    class="multi-form theme-input"
                    type="password"
                    required
                    placeholder="New password"
                />
                <h2 class="theme-h2 field-heading">
                    Repeat new password
                </h2>
                <b-input
                    v-model="passwordRepeated"
                    class="multi-form theme-input"
                    type="password"
                    required
                    placeholder="Repeat new password"
                />
                <b-button
                    class="float-right green-button"
                    type="submit"
                >
                    <icon name="save"/>
                    Save
                </b-button>
            </b-form>
        </b-card>
    </content-single-column>
</template>

<script>
import contentSingleColumn from '@/components/columns/ContentSingleColumn.vue'
import tooltip from '@/components/assets/Tooltip.vue'

import authAPI from '@/api/auth.js'
import validation from '@/utils/validation.js'

import { mapGetters } from 'vuex'

export default {
    name: 'SetPassword',
    components: {
        contentSingleColumn,
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
        computed: {
            ...mapGetters({
                instanceName: 'instance/name',
            }),
        },
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
            return `To continue using ${this.instanceName}, please please set a new password below. `
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
