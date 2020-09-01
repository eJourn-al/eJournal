<template>
    <b-card class="no-hover">
        <h2 class="theme-h2 multi-form">
            Select an assignment to link
        </h2>
        <p>
            This action will create a link between the eJournal assignment of your choice and the LMS (Canvas)
            assignment. Students with existing journals for the eJournal assignment will be able to continue their work
            after visiting the new assignment on Canvas at least once.
        </p>
        <theme-select
            v-model="selectedCourse"
            label="name"
            trackBy="id"
            :options="courses"
            :multiple="false"
            :searchable="true"
            placeholder="Select A Course"
            class="multi-form"
            @select="() => {
                selectedAssignment = null
            }"
        />
        <theme-select
            v-if="selectedCourse"
            v-model="selectedAssignment"
            label="name"
            trackBy="id"
            :options="assignments"
            :multiple="false"
            :searchable="true"
            placeholder="Select An Assignment"
            class="multi-form"
        />

        <div v-if="selectedAssignment !== null">
            <hr/>
            <b-button
                class="change-button float-right"
                type="submit"
                @click="linkAssignment"
            >
                <icon name="link"/>
                Link
            </b-button>
        </div>
    </b-card>
</template>

<script>
import assignmentAPI from '@/api/assignment.js'

export default {
    name: 'LinkAssignment',
    props: ['linkableAssignments'],
    data () {
        return {
            selectedCourse: null,
            selectedAssignment: null,
        }
    },
    computed: {
        courses () {
            return this.linkableAssignments.map((linkable) => {
                const course = { ...linkable.course }
                if (course.startdate || course.enddate) {
                    course.name += ` (${course.startdate ? course.startdate.substring(0, 4) : ''} - ${
                        course.enddate ? course.enddate.substring(0, 4) : ''})`
                }

                return course
            })
        },
        assignments () {
            return this.linkableAssignments.find(linkable => linkable.course.id === this.selectedCourse.id)
                .assignments
        },
    },
    methods: {
        linkAssignment () {
            const ltiCount = this.selectedAssignment.lti_courses ? this.selectedAssignment.lti_courses.length : 0
            if (!ltiCount || window.confirm(
                `This assignment is already linked to ${ltiCount > 1 ? `${ltiCount} ` : 'an'}`
                + `other assignment${ltiCount > 1 ? 's' : ''} on the LMS (Canvas). Are you sure you want to`
                + ' link this one as well? Grades will only be passed back to the new link.')) {
                assignmentAPI.update(this.selectedAssignment.id, { launch_id: this.$route.query.launch_id })
                    .then((assignment) => { this.$emit('assignmentLinked', assignment) })
                    // .catch((error) => {
                    //     if (error.response.status === 400
                    //         && error.response.data.description.startsWith(
                    //             'You cannot unpublish an assignment that already has submissions')) {
                    //         this.$toasted.error(
                    //             `The new assignment on the LMS (Canvas) is unpublished, but the existing eJournal
                    //             assignment you are trying to link already contains entries. Publish the assignment on
                    //             Canvas, then visit the assignment page there again to link it to eJournal.`,
                    //             { duration: 12000 },
                    //         )
                    //     }
                    // })
            }
        },
    },
}
</script>
