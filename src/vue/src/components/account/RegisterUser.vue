<template>
    <div>
        <b-form
            @submit.prevent="onSubmit"
            @reset.prevent="onReset"
        >
            <template v-if="!$route.query.launch_id">
                <h2
                    class="theme-h2 field-heading required"
                >
                    Username
                </h2>
                <b-input
                    v-model="form.username"
                    class="multi-form theme-input"
                    placeholder="Username"
                    maxlength="30"
                    required
                />
                <h2
                    class="theme-h2 field-heading required"
                >
                    Full name
                </h2>
                <b-input
                    v-model="form.fullName"
                    class="multi-form theme-input"
                    placeholder="Full name"
                    maxlength="200"
                    required
                />
                <h2
                    class="theme-h2 field-heading required"
                >
                    Email
                </h2>
                <b-input
                    v-model="form.email"
                    class="multi-form theme-input"
                    placeholder="Email"
                    required
                />
            </template>
            <h2 class="theme-h2 field-heading required">
                New password
                <tooltip
                    tip="Should contain at least 8 characters, a capital letter and a special character"
                />
            </h2>
            <b-input
                v-model="form.password"
                class="multi-form theme-input"
                type="password"
                placeholder="Password"
                required
            />
            <h2 class="theme-h2 field-heading required">
                Repeat new password
            </h2>
            <b-input
                v-model="form.password2"
                class="multi-form theme-input"
                type="password"
                placeholder="Repeat password"
                required
            />
            <b-button
                class="float-left orange-button multi-form"
                type="reset"
            >
                <icon name="undo"/>
                Reset
            </b-button>
            <b-button
                class="float-right multi-form"
                :class="{ 'input-disabled': saveRequestInFlight }"
                type="submit"
            >
                <icon name="user-plus"/>
                Create account
            </b-button>
        </b-form>
    </div>
</template>

<script>
import tooltip from '@/components/assets/Tooltip.vue'

import authAPI from '@/api/auth.js'
import validation from '@/utils/validation.js'

export default {
    name: 'RegisterUser',
    components: {
        tooltip,
    },
    data () {
        return {
            form: {
                username: '',
                password: '',
                password2: '',
                fullName: '',
                email: '',
            },
            saveRequestInFlight: false,
        }
    },
    methods: {
        onSubmit () {
            this.saveRequestInFlight = true

            if (validation.validatePassword(this.form.password, this.form.password2)
                && (this.$route.query.launch_id || validation.validateEmail(this.form.email))) {
                authAPI.register(
                    this.form.username,
                    this.form.password,
                    this.form.fullName,
                    this.form.email,
                    this.$route.query.launch_id,
                    {
                        customSuccessToast: this.$route.query.launch_id ? ''
                            : `Registration successful! Please follow the
                            instructions sent to ${this.form.email} to confirm your email address.`,
                    })
                    .then((user) => {
                        if (this.$route.query.launch_id) {
                            this.$route.query.launch_state = user.launch_state
                        }
                        this.$store.dispatch(
                            'user/login',
                            { username: user.username, password: this.form.password },
                        )
                            .then(() => {
                                this.$emit('handleAction')
                            })
                    })
                    .finally(() => {
                        this.saveRequestInFlight = false
                    })
            } else {
                this.saveRequestInFlight = false
            }
        },
        onReset () {
            this.form = {
                username: '',
                password: '',
                password2: '',
                fullName: '',
                email: '',
            }
        },
    },
}
</script>
