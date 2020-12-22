<template>
    <b-card
        :class="$root.getBorderClass(user.id)"
        class="no-hover"
    >
        <div class="float-left">
            <b>{{ user.full_name }}</b><br/>
            {{ user.username }}
        </div>
        <b-button
            v-if="$hasPermission('can_add_course_users')"
            class="green-button float-right"
            @click.prevent.stop="addUserToCourse()"
        >
            <icon name="user-plus"/>
            Add
        </b-button>
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
    },
    methods: {
        addUserToCourse () {
            if (window.confirm(`Are you sure you want to add "${this.user.full_name}" to this course?`)) {
                participationAPI.create({ course_id: this.cID, user_id: this.user.id })
                    .then(() => { this.$emit('add-participant', this.user) })
            }
        },
    },
}
</script>
