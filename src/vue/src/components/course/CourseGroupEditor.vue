<template>
    <div>
        <h4 class="theme-h4 mb-2">
            <span>Groups</span>
        </h4>
        <group-card
            v-for="g in groups"
            :key="g.id"
            :participants="participants"
            :cID="course.id"
            :group="g"
            @delete-group="deleteGroup"
            @update-group="updateGroup"
            @remove-member="removeMember"
        />

        <div v-if="$hasPermission('can_add_course_user_group')">
            <h4 class="theme-h4 mb-2">
                <span>Create new group</span>
            </h4>
            <b-card class="no-hover">
                <b-form
                    @submit.prevent="createUserGroup"
                    @reset.prevent="resetFormInput"
                >
                    <b-input
                        v-model="form.groupName"
                        class="new-group-input multi-form mr-2 theme-input"
                        placeholder="Desired group name"
                        required
                    />
                    <b-button
                        class="add-button float-right"
                        type="submit"
                    >
                        <icon name="plus-square"/>
                        Create
                    </b-button>
                </b-form>
                <b-button
                    v-if="course.lti_linked"
                    class="lti-sync multi-form mr-2"
                    type="submit"
                    @click.prevent.stop="getDataNoseGroups()"
                >
                    <icon name="sync-alt"/>
                    Sync from DataNose
                </b-button>
                <b-button
                    v-if="course.lti_linked"
                    class="lti-sync multi-form mr-2"
                    type="submit"
                    @click.prevent.stop="getLMSGroups()"
                >
                    <icon name="sync-alt"/>
                    Sync from LMS
                </b-button>
            </b-card>
        </div>
    </div>
</template>
<style lang="sass">
.new-group-input
    margin-bottom: 0px !important

.lti-sync
    margin-bottom: 0px !important
    margin-top: 10px !important
</style>

<script>
import groupCard from '@/components/group/GroupCard.vue'
import groupAPI from '@/api/group.js'
import participationAPI from '@/api/participation.js'

export default {
    name: 'CourseGroupEditor',
    components: {
        groupCard,
    },
    props: {
        course: {
            required: true,
        },
    },
    data () {
        return {
            form: {
                groupName: '',
                lti_id: '',
            },
            participants: [],
            groups: [],
        }
    },
    created () {
        groupAPI.getAllFromCourse(this.course.id)
            .then((groups) => { this.groups = groups })
        participationAPI.getEnrolled(this.course.id)
            .then((participants) => { this.participants = participants })
    },
    methods: {
        getDataNoseGroups () {
            groupAPI.getDataNose(this.course.id, { customSuccessToast: 'Successfully syncronized from DataNose.' })
        },
        getLMSGroups () {
            groupAPI.getLMS(this.course.id, { customSuccessToast: 'Successfully syncronized from DataNose.' })
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
            this.groups = this.groups.filter(g => g.id !== group.id)
        },
        updateGroup (participants, group) {
            this.participants = participants
            this.$emit('update-group', group)
        },
        removeMember (member, group) {
            this.participants.forEach((participant) => {
                if (participant.id === member.id) {
                    participant.groups = participant.groups.filter(g => g.id !== group.id)
                }
            })
        },
    },
}
</script>
