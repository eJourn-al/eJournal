<template>
    <div>
        <b-card
            v-if="editing"
            class="no-hover"
        >
            <b-button
                class="float-right"
                type="submit"
                @click="editing = false"
            >
                <icon name="times"/>
                Stop editing
            </b-button>
            <b-form @submit.prevent="updateGroupName">
                <h2 class="theme-h2 field-heading">
                    Group name
                </h2><br/>
                <div class="d-flex">
                    <b-input
                        v-model="group.name"
                        :readonly="!$hasPermission('can_edit_course_user_group')"
                        class="multi-form  mr-2 theme-input"
                        required
                        placeholder="Group name"
                    />
                    <b-button
                        class="green-button multi-form"
                        type="submit"
                    >
                        <icon name="save"/>
                        Save
                    </b-button>
                </div>
            </b-form>
            <h2 class="theme-h2 field-heading">
                Members
            </h2>
            <ul
                v-if="$hasPermission('can_edit_course_user_group')"
                class="member-list"
            >
                <li
                    v-for="member in members"
                    :key="member.id"
                >
                    <b>{{ member.full_name }}</b> ({{ member.username }})
                    <b-button
                        class="float-right red-button"
                        type="submit"
                        @click.stop
                        @click="removeUser(member)"
                    >
                        <icon name="user-times"/>
                        Remove
                    </b-button>
                </li>
            </ul>

            <div v-if="$hasPermission('can_edit_course_user_group')">
                <div class="d-flex">
                    <theme-select
                        v-model="participantsToAdd"
                        label="full_name"
                        trackBy="id"
                        :options="notMembers"
                        :multiple="true"
                        :searchable="true"
                        :multiSelectText="`user${participantsToAdd &&
                            participantsToAdd.length === 1 ? '' : 's'} selected`"
                        placeholder="Select Users To Add"
                        class="multi-form no-right-radius"
                    />
                    <b-button
                        class="green-button multi-form no-left-radius"
                        @click.prevent.stop="addToGroup()"
                    >
                        <icon name="user-plus"/>
                        Add
                    </b-button>
                </div>
            </div>

            <b-button
                v-if="$hasPermission('can_delete_course_user_group')"
                class="float-left red-button"
                @click.prevent.stop="removeGroup()"
            >
                <icon name="trash"/>
                Delete group
            </b-button>
        </b-card>
        <b-card
            v-else
            class="hover"
            @click="editing = true"
        >
            <span class="float-left">
                <h2 class="theme-h2 field-heading">{{ group.name }}</h2>
                {{ members.length }} {{ members.length === 1 ? "member" : "members" }}
            </span>
        </b-card>
    </div>
</template>

<style lang="sass">
.member-list
    padding: 0
    margin-bottom: 0
    li
        list-style-type: none
        line-height: 3em
        padding-bottom: 7px
        margin-bottom: 7px
        border-bottom: 1px solid #eee
    li:last-child
        border-bottom: none

</style>

<script>
import groupAPI from '@/api/group.js'

export default {
    props: {
        cID: {
            required: true,
        },
        group: {
            required: true,
        },
        participants: {
            required: true,
        },
    },
    data () {
        return {
            form: {
                newGroupName: '',
            },
            editing: false,
            participantsToAdd: [],
        }
    },
    computed: {
        notMembers () {
            return this.participants.filter((p) => !this.members.map((m) => m.id).includes(p.id))
        },
        members () {
            return this.participants.filter((p) => p.groups.map((g) => g.id).includes(this.group.id))
        },
    },
    methods: {
        updateGroupName () {
            groupAPI.update(this.group.id, {
                name: this.group.name,
            }, { customSuccessToast: 'Successfully updated the group.' })
                .then((group) => {
                    this.group = group
                    this.form.newGroupName = ''
                })
        },
        removeGroup () {
            if (window.confirm(`Are you sure you want to remove ${this.group.name} from this course?`)) {
                groupAPI.delete(this.group.id, { responseSuccessToast: true }).then(() => {
                    this.$emit('delete-group', this.group)
                })
            }
        },
        removeUser (member) {
            groupAPI.removeMember(
                this.group.id,
                member.id,
                { customSuccessToast: `Removed ${member.full_name} from ${this.group.name}.` },
            )
                .then(() => { this.$emit('remove-member', member, this.group) })
        },
        addToGroup () {
            for (let i = 0; i < this.participantsToAdd.length; i++) {
                groupAPI.addMember(
                    this.group.id,
                    this.participantsToAdd[i].id,
                    { customSuccessToast: `Added ${this.participantsToAdd[i].full_name} to ${this.group.name}.` },
                )
                    .then((participants) => {
                        this.$emit('update-group', participants, this.group)
                        this.participantsToAdd = []
                    })
            }
        },
    },
}
</script>
