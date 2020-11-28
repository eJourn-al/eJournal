<template>
    <b-card
        :class="$root.getBorderClass($route.params.uID)"
        class="no-hover multi-form"
    >
        <b-form @submit.prevent="changePassword()">
            <b-input
                name="username"
                autocomplete="username"
                hidden
            />
            <h2 class="theme-h2 field-heading">
                Current password
            </h2>
            <b-input
                v-model="oldPass"
                class="theme-input multi-form"
                type="password"
                placeholder="Current password"
                autocomplete="new-password"
            />
            <h2 class="theme-h2 field-heading required">
                New password
                <tooltip
                    tip="Should contain at least 8 characters, a capital letter and a special character"
                />
            </h2>
            <b-input
                v-model="newPass"
                class="theme-input multi-form"
                type="password"
                placeholder="New password"
                autocomplete="new-password"
            />
            <h2 class="theme-h2 field-heading">
                Repeat new password
            </h2>
            <b-input
                v-model="newPassRepeat"
                class="theme-input multi-form"
                type="password"
                placeholder="Repeat new password"
                autocomplete="new-password"
            />
            <b-button
                type="submit"
                class="green-button float-right"
            >
                <icon name="save"/>
                Save
            </b-button>
        </b-form>
    </b-card>
</template>

<script>
import tooltip from '@/components/assets/Tooltip.vue'

import validation from '@/utils/validation.js'
import authAPI from '@/api/auth.js'

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
        isChanged () {
            return (this.oldPass !== '' || this.newPass !== '' || this.newPassRepeat !== '')
        },
    },
}
</script>
