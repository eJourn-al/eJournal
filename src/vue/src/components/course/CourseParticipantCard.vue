<template>
    <b-card>
        <b-row>
            <b-col
                sm="8"
                class="d-flex mb-2"
            >
                <b-col
                    cols="3"
                    class="text-center"
                >
                    <img
                        :src="user.profile_picture"
                        class="theme-img profile-picture-sm"
                    />
                </b-col>
                <b-col cols="9">
                    <b>{{ user.full_name }}</b> ({{ user.role }})<br/>
                    {{ user.username }}<br/>
                    <span
                        v-for="group in user.groups"
                        :key="group.id"
                    >{{ group.name }} </span>
                </b-col>
            </b-col>
            <b-col sm="4">
                <div :class="{ 'input-disabled': numTeachers === 1 && selectedRole === 'Teacher'}">
                    <b-form-select
                        v-if="$hasPermission('can_edit_course_roles')"
                        v-model="selectedRole"
                        :selectSize="1"
                        class="theme-select"
                    >
                        <option
                            v-for="r in roles"
                            :key="r.name"
                            :value="r.name"
                        >
                            {{ r.name }}
                        </option>
                    </b-form-select>
                    <b-button
                        v-if="$hasPermission('can_delete_course_users')"
                        class="red-button full-width"
                        @click.prevent.stop="removeFromCourse()"
                    >
                        <icon name="user-times"/>
                        Remove
                    </b-button>
                </div>
            </b-col>
        </b-row>
    </b-card>
</template>

<script>
import participationAPI from '@/api/participation.js'

export default {
    props: {
        cID: {
            required: true,
        },
        user: {
            required: true,
        },
        roles: {
            required: true,
        },
        numTeachers: {
            required: true,
        },
    },
    data () {
        return {
            selectedRole: '',
            selectedGroup: '',
            init: 2,
        }
    },
    watch: {
        selectedRole (val) {
            if (this.init > 0) {
                this.init--
            } else {
                this.selectedRole = val
                this.$emit('update:role', val)
                this.$emit('update-participants', val, this.user.id)
                participationAPI.update(
                    this.cID,
                    { user_id: this.user.id, role: this.selectedRole, group: this.selectedGroup },
                ).then(() => {
                    if (this.$store.getters['user/uID'] === this.user.id) {
                        this.$store.dispatch('user/populateStore').then(() => {
                            this.$router.push({ name: 'Course', params: { cID: this.cID } })
                        }, () => {
                            this.$toasted.error('The website might be out of sync, please login again.')
                        })
                    }
                })
            }
        },
        selectedGroup (val) {
            if (this.init > 0) {
                this.init--
            } else {
                this.selectedGroup = val
                this.$emit('update:group', val)
                participationAPI.update(
                    this.cID, { user_id: this.user.id, group: this.selectedGroup, role: this.selectedRole })
            }
        },
        group (newVal) {
            this.selectedGroup = newVal
        },
    },
    created () {
        this.selectedRole = this.user.role
        this.selectedGroup = this.group
    },
    methods: {
        removeFromCourse () {
            if (window.confirm(`Are you sure you want to remove "${this.user.full_name}" from this course?`)) {
                participationAPI.delete(this.cID, this.user.id, { responseSuccessToast: true }).then(() => {
                    if (this.$store.getters['user/uID'] === this.user.id) {
                        this.$store.dispatch('user/populateStore').catch(() => {
                            this.$toasted.error('The website might be out of sync, please login again.')
                        })
                        this.$router.push({ name: 'Home' })
                    }
                    this.$emit('delete-participant', this.user)
                })
            }
        },
    },
}
</script>
