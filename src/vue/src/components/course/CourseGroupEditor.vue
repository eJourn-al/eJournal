<template>
    <load-wrapper :loading="loadingGroups">
        <group-card
            v-for="g in groups"
            :key="g.id"
            :participants="participants"
            :cID="cID"
            :group="g"
            @delete-group="deleteGroup"
            @update-group="updateGroup"
            @remove-member="removeMember"
        />
        <i
            v-if="!groups.length"
            class="text-grey"
        >
            No existing groups
        </i>

        <template v-if="$hasPermission('can_add_course_user_group')">
            <b-form
                class="d-flex mt-2"
                @submit.prevent="createUserGroup"
                @reset.prevent="resetFormInput"
            >
                <b-input
                    v-model="form.groupName"
                    class="new-group-input mr-2"
                    placeholder="Enter new group name..."
                    required
                />
                <b-button
                    class="green-button float-right"
                    type="submit"
                >
                    <icon name="plus-square"/>
                    Create
                </b-button>
            </b-form>
            <b-button
                v-if="course.lti_linked"
                class="lti-sync mb-2 mr-2"
                type="submit"
                @click.prevent.stop="getDataNoseGroups()"
            >
                <icon name="sync-alt"/>
                Sync groups from DataNose
            </b-button>
        </template>
    </load-wrapper>
</template>
<style lang="sass">
.new-group-input
    margin-bottom: 0px !important

.lti-sync
    margin-bottom: 0px !important
    margin-top: 10px !important
</style>

<script>
import GroupCard from '@/components/group/GroupCard.vue'
import LoadWrapper from '@/components/loading/LoadWrapper.vue'

import courseAPI from '@/api/course.js'
import groupAPI from '@/api/group.js'
import participationAPI from '@/api/participation.js'

export default {
    name: 'CourseGroupEditor',
    components: {
        GroupCard,
        LoadWrapper,
    },
    props: {
        cID: {
            required: true,
        },
    },
    data () {
        return {
            form: {
                groupName: '',
                lti_id: '',
            },
            course: {},
            participants: [],
            groups: [],
            loadingGroups: true,
        }
    },
    created () {
        courseAPI.get(this.cID)
            .then((course) => {
                this.course = course

                groupAPI.getAllFromCourse(course.id)
                    .then((groups) => {
                        this.groups = groups
                        this.loadingGroups = false
                    })
                participationAPI.getEnrolled(course.id)
                    .then((participants) => { this.participants = participants })
            })
    },
    methods: {
        getDataNoseGroups () {
            groupAPI.getDataNose(this.course.id, { customSuccessToast: 'Successfully syncronized from DataNose.' })
        },
        createUserGroup () {
            groupAPI.create({ name: this.form.groupName, course_id: this.course.id, lti_id: this.course.lti_id },
                { customSuccessToast: 'Successfully created group.' })
                .then((group) => {
                    this.groups.push(group)
                    this.resetFormInput()
                })
        },
        resetFormInput () {
            /* Reset form values */
            this.form.groupName = ''
        },
        deleteGroup (group) {
            this.groups = this.groups.filter((g) => g.id !== group.id)
        },
        updateGroup (participants, group) {
            this.participants = participants
            this.$emit('update-group', group)
        },
        removeMember (member, group) {
            this.participants.forEach((participant) => {
                if (participant.id === member.id) {
                    participant.groups = participant.groups.filter((g) => g.id !== group.id)
                }
            })
        },
    },
}
</script>
