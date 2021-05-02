<template>
    <b-modal
        ref="linkCourseRef"
        title="Link Course"
        size="lg"
        noEnforceFocus
    >
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
            class="mb-2"
        />
        <template #modal-footer>
            <b-button
                class="orange-button"
                :class="{ 'input-disabled': selectedCourse === null }"
                @click="linkCourse"
            >
                <icon name="link"/>
                Link
            </b-button>
        </template>
    </b-modal>
</template>

<script>
import courseAPI from '@/api/course.js'
import utils from '@/utils/generic_utils.js'

export default {
    name: 'LinkCourse',
    props: ['courses'],
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
            courseAPI.update(this.selectedCourse.id, { launch_id: this.$route.query.launch_id })
                .then((course) => { this.$emit('courseLinked', course) })
        },
        show () {
            this.$refs.linkCourseRef.show()
        },
        hide () {
            this.$refs.linkCourseRef.hide()
        },
    },
}
</script>
