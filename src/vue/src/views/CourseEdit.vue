<!-- TODO: You shouldnt be able to change your own role. -->
<template>
    <content-columns>
        <bread-crumb slot="main-content-column"/>

        <div
            v-if="activeView === 'courseData'"
            slot="main-content-column"
        >
            <detail-editor
                :course="course"
                @update-course="updateCourse"
            />
        </div>

        <div
            v-if="activeView === 'courseMembers'"
            slot="main-content-column"
        >
            <members-editor :course="course"/>
        </div>

        <div
            v-if="activeView === 'courseGroups'"
            slot="main-content-column"
        >
            <group-editor :course="course"/>
        </div>

        <div slot="right-content-column">
            <h3 class="theme-h3">
                Actions
            </h3>
            <b-button
                v-if="$hasPermission('can_edit_course_details')"
                class="multi-form orange-button full-width"
                @click="activeView = 'courseData'"
            >
                <icon name="edit"/>
                Manage Details
            </b-button>
            <b-button
                v-if="$hasPermission('can_edit_course_details')"
                class="multi-form orange-button full-width"
                @click="activeView = 'courseMembers'"
            >
                <icon name="user"/>
                Manage Members
            </b-button>
            <b-button
                v-if="$hasPermission('can_edit_course_details')"
                class="multi-form orange-button full-width"
                @click="activeView = 'courseGroups'"
            >
                <icon name="users"/>
                Manage Groups
            </b-button>
            <b-button
                v-if="$hasPermission('can_edit_course_roles')"
                class="multi-form orange-button full-width"
                @click.prevent.stop="$router.push({ name: 'UserRoleConfiguration', params: { cID: cID } })"
            >
                <icon name="cog"/>
                Manage Permissions
            </b-button>
            <b-button
                v-if="$hasPermission('can_delete_course')"
                class="multi-form red-button full-width"
                @click.prevent.stop="deleteCourse()"
            >
                <icon name="trash"/>
                Delete Course
            </b-button>
        </div>
    </content-columns>
</template>

<script>
import breadCrumb from '@/components/assets/BreadCrumb.vue'
import contentColumns from '@/components/columns/ContentColumns.vue'
import groupEditor from '@/components/course/CourseGroupEditor.vue'
import detailEditor from '@/components/course/CourseDetailEditor.vue'
import membersEditor from '@/components/course/CourseMembersEditor.vue'

import store from '@/Store.vue'
import courseAPI from '@/api/course.js'

export default {
    name: 'CourseEdit',
    components: {
        breadCrumb,
        contentColumns,
        detailEditor,
        membersEditor,
        groupEditor,
    },
    props: {
        cID: {
            required: true,
        },
    },
    data () {
        return {
            activeView: 'courseData',
            course: {},
        }
    },
    created () {
        courseAPI.get(this.cID)
            .then((course) => {
                this.course = course
                if (!this.course.startdate) {
                    this.course.startdate = ''
                }
                if (!this.course.enddate) {
                    this.course.enddate = ''
                }
                this.originalCourse = this.deepCopyCourse(course)
            })
    },
    methods: {
        deleteCourse () {
            if (window.confirm(`Are you sure you want to delete ${this.course.name}?`)) {
                courseAPI.delete(this.cID)
                    .then(() => { this.$router.push({ name: 'Home' }) })
            }
        },
        deepCopyCourse (course) {
            const copyCourse = {
                name: course.name,
                abbreviation: course.abbreviation,
                startdate: course.startdate,
                enddate: course.enddate,
            }

            return copyCourse
        },
        checkChanged () {
            if (this.course.name !== this.originalCourse.name
                || this.course.abbreviation !== this.originalCourse.abbreviation
                || this.course.startdate !== this.originalCourse.startdate
                || this.course.enddate !== this.originalCourse.enddate) {
                return true
            }

            return false
        },
        updateCourse (course) {
            this.course = course
            this.originalCourse = this.deepCopyCourse(course)
            store.clearCache()
        },
    },
    beforeRouteLeave (to, from, next) {
        if (this.checkChanged() && !window.confirm(
            'Unsaved changes in "Manage Details" will be lost if you leave. Do you wish to continue?')
        ) {
            next(false)
            return
        }

        next()
    },
}
</script>
