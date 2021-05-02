<!-- TODO: You shouldnt be able to change your own role. -->
<template>
    <wide-content>
        <bread-crumb/>
        <b-card noBody>
            <b-tabs
                card
                pills
                lazy
            >
                <b-tab v-if="$hasPermission('can_edit_course_details')">
                    <template slot="title">
                        <icon
                            name="edit"
                            class="shift-up-3"
                        />
                        Course Details
                    </template>
                    <detail-editor
                        :cID="cID"
                    />
                </b-tab>
                <b-tab v-if="$hasPermission('can_edit_course_details')">
                    <template slot="title">
                        <icon
                            name="user"
                            class="shift-up-3"
                        />
                        Members
                    </template>
                    <members-editor :cID="cID"/>
                </b-tab>
                <b-tab v-if="$hasPermission('can_edit_course_details')">
                    <template slot="title">
                        <icon
                            name="users"
                            class="shift-up-3"
                        />
                        Groups
                    </template>
                    <group-editor :cID="cID"/>
                </b-tab>
                <b-tab :titleLinkClass="'mr-2'">
                    <template slot="title">
                        <icon
                            name="user-shield"
                            class="shift-up-3"
                        />
                        Permissions
                    </template>
                    <user-role-configuration :cID="cID"/>
                </b-tab>
                <b-tab
                    v-if="$hasPermission('can_delete_course')"
                    :titleLinkClass="'background-red text-white'"
                >
                    <template slot="title">
                        <icon
                            name="exclamation"
                            class="shift-up-3"
                        />
                        Danger Zone
                    </template>
                    <b-card class="border-red">
                        <b-button
                            class="red-button float-right ml-2 mb-2"
                            @click.prevent.stop="deleteCourse()"
                        >
                            <icon name="trash"/>
                            Delete Course
                        </b-button>
                        <h2 class="theme-h2 text-red">
                            Delete course
                        </h2>
                        <span class="small">
                            <b>Warning:</b>
                            This action is irreversible and will cause loss of all assignments and
                            journals associated with this course.
                        </span>
                    </b-card>
                </b-tab>
            </b-tabs>
        </b-card>
    </wide-content>
</template>

<script>
import breadCrumb from '@/components/assets/BreadCrumb.vue'
import detailEditor from '@/components/course/CourseDetailEditor.vue'
import groupEditor from '@/components/course/CourseGroupEditor.vue'
import membersEditor from '@/components/course/CourseMembersEditor.vue'
import userRoleConfiguration from '@/components/course/UserRoleConfiguration.vue'
import wideContent from '@/components/columns/WideContent.vue'

import courseAPI from '@/api/course.js'
import store from '@/Store.vue'

export default {
    name: 'CourseEdit',
    components: {
        breadCrumb,
        wideContent,
        detailEditor,
        membersEditor,
        groupEditor,
        userRoleConfiguration,
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
            const confirm = window.prompt('Are you sure you want delete this course? All corresponding assignments and '
                + 'journals will be irreversibly lost! Type \'delete\' to confirm', '')
            if (confirm === null || confirm.toLowerCase() !== 'delete') {
                return
            }

            courseAPI.delete(this.cID)
                .then(() => { this.$router.push({ name: 'Home' }) })
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
        updateCourse () {
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
