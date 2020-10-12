<template>
    <content-single-column>
        <h1 class="theme-h1">
            <span>Password Recovery</span>
        </h1>
        <b-card class="no-hover">
            <b-form @submit.prevent="recoverPassword()">
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
                    class="float-right multi-form add-button"
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

export default {
    name: 'PasswordRecovery',
    components: {
        contentSingleColumn,
        tooltip,
    },
    props: ['username', 'recoveryToken'],
    data () {
        return {
            password: '',
            passwordRepeated: '',
        }
    },
    methods: {
        recoverPassword () {
            if (validation.validatePassword(this.password, this.passwordRepeated)) {
                authAPI.recoverPassword(
                    this.username,
                    this.recoveryToken,
                    this.password,
                    { responseSuccessToast: true },
                )
                    .then(() => { this.$router.push({ name: 'Login' }) })
            }
        },
    },
}
</script>
