<template>
    <b-card class="no-hover">
        <h2 class="theme-h2 field-heading">
            Select a course to link
        </h2>
        <p>
            Select the eJournal course that you want to link to the current LMS (Canvas) course below. This action will
            overwrite an existing link between Canvas and this eJournal course, so proceed with caution.
        </p>
        <theme-select
            v-model="selectedCourse"
            label="name"
            trackBy="id"
            :options="coursesWithDates"
            :multiple="false"
            :searchable="true"
            placeholder="Select A Course"
            class="multi-form"
        />
        <div v-if="selectedCourse !== null">
            <hr/>

            <b-button
                class="change-button float-right"
                @click="linkCourse"
            >
                <icon name="link"/>
                Link
            </b-button>
        </div>
    </b-card>
</template>

<script>
import courseAPI from '@/api/course.js'
import utils from '@/utils/generic_utils.js'

export default {
    name: 'LinkCourse',
    props: ['lti', 'courses'],
    data () {
        return {
            selectedCourse: null,
        }
    },
    computed: {
        coursesWithDates () {
            return this.courses.map((course) => {
                const courseCopy = { ...course }
                courseCopy.name = utils.courseWithDatesDisplay(courseCopy)
                return courseCopy
            })
        },
    },
    methods: {
        linkCourse () {
            courseAPI.update(this.selectedCourse.id, { lti_id: this.lti.ltiCourseID })
                .then((course) => { this.$emit('handleAction', course.id) })
        },
    },
}
</script>
