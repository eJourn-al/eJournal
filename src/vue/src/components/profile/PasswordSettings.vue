<template>
    <b-form @submit.prevent="changePassword()">
        <b-input
            name="username"
            autocomplete="username"
            hidden
        />

        <b-form-group
            label="Current password"
            required
        >
            <b-form-input
                v-model="oldPass"
                type="password"
                autofocus
                placeholder="Current password"
                autocomplete="current-password"
                required
            />
        </b-form-group>

        <b-form-group required>
            <template #label>
                New password
                <tooltip tip="Should contain at least 8 characters, a capital letter and a special character"/>
            </template>

            <b-form-input
                v-model="newPass"
                type="password"
                placeholder="New password"
                autocomplete="new-password"
                required
            />
        </b-form-group>

        <b-form-group
            label="Repeat new password"
            required
        >
            <b-form-input
                v-model="newPassRepeat"
                type="password"
                placeholder="Repeat new password"
                autocomplete="new-password"
                required
            />
        </b-form-group>

        <b-button
            class="green-button float-right mb-2"
            type="submit"
        >
            <icon name="save"/>
            Save
        </b-button>
    </b-form>
</template>

<script>
import tooltip from '@/components/assets/Tooltip.vue'

import authAPI from '@/api/auth.js'
import validation from '@/utils/validation.js'

export default {
    components: {
        tooltip,
    },
    data () {
        return {
            checkbox: false,
            oldPass: '',
            newPass: '',
            newPassRepeat: '',
        }
    },
    methods: {
        changePassword () {
            if (validation.validatePassword(this.newPass, this.newPassRepeat)) {
                authAPI.changePassword(this.newPass, this.oldPass, { responseSuccessToast: true })
                    .then(() => {
                        this.oldPass = ''
                        this.newPass = ''
                        this.newPassRepeat = ''
                    })
            }
        },
    },
}
</script>
