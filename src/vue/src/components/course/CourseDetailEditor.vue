<template>
    <load-wrapper :loading="originalData === null">
        <b-form @submit.prevent="onSubmit">
            <b-alert
                :show="unsavedChanges"
            >
                <b>Note</b>: changes are not saved.
            </b-alert>
            <h2 class="theme-h2 field-heading required">
                Course name
            </h2>
            <b-input
                v-model="course.name"
                class="mb-2"
                :readonly="!$hasPermission('can_edit_course_details')"
                placeholder="Course name"
            />
            <h2 class="theme-h2 field-heading required">
                Course abbreviation
            </h2>
            <b-input
                v-model="course.abbreviation"
                class="mb-2"
                :readonly="!$hasPermission('can_edit_course_details')"
                maxlength="10"
                placeholder="Course abbreviation (max 10 characters)"
            />
            <b-row>
                <b-col cols="6">
                    <h2 class="theme-h2 field-heading">
                        Start date
                        <tooltip tip="Start date of the course"/>
                    </h2>
                    <reset-wrapper v-model="course.startdate">
                        <flat-pickr
                            v-model="course.startdate"
                            class="mb-2 full-width"
                            :class="{ 'input-disabled': !$hasPermission('can_edit_course_details') }"
                            :config="startDateConfig"
                        />
                    </reset-wrapper>
                </b-col>
                <b-col cols="6">
                    <h2 class="theme-h2 field-heading">
                        End date
                        <tooltip tip="End date of the course"/>
                    </h2>
                    <reset-wrapper v-model="course.enddate">
                        <flat-pickr
                            v-model="course.enddate"
                            class="mb-2 full-width"
                            :class="{ 'input-disabled': !$hasPermission('can_edit_course_details') }"
                            :config="endDateConfig"
                        />
                    </reset-wrapper>
                </b-col>
            </b-row>
            <b-button
                v-if="unsavedChanges"
                class="green-button float-right mb-2"
                type="submit"
            >
                <icon name="save"/>
                Save
            </b-button>
        </b-form>
    </load-wrapper>
</template>

<script>
import LoadWrapper from '@/components/loading/LoadWrapper.vue'
import Tooltip from '@/components/assets/Tooltip.vue'
import courseAPI from '@/api/course.js'

export default {
    name: 'CourseEdit',
    components: {
        LoadWrapper,
        Tooltip,
    },
    props: {
        cID: {
            required: true,
        },
    },
    data () {
        return {
            course: {},
            originalData: null,
        }
    },
    computed: {
        startDateConfig () {
            const additionalConfig = {}
            if (this.course.enddate) {
                additionalConfig.maxDate = new Date(this.course.enddate)
            }
            return { ...additionalConfig, ...this.$root.flatPickrTimeConfig }
        },
        endDateConfig () {
            const additionalConfig = {}
            if (this.course.startdate) {
                additionalConfig.minDate = new Date(this.course.startdate)
            }
            return { ...additionalConfig, ...this.$root.flatPickrTimeConfig }
        },
        unsavedChanges () {
            return this.originalData !== null && JSON.stringify(this.course, this.replacer) !== this.originalData
        },
    },
    created () {
        courseAPI.get(this.cID)
            .then((course) => {
                this.course = course
                this.originalData = JSON.stringify(course, this.replacer)
            })
    },
    methods: {
        formFilled () {
            return this.course.name && this.course.abbreviation
        },
        onSubmit () {
            if (this.formFilled()) {
                courseAPI.update(
                    this.course.id,
                    this.course,
                    { customSuccessToast: 'Successfully updated the course.' },
                )
                    .then((course) => {
                        this.course = course
                        this.originalData = JSON.stringify(course, this.replacer)
                    })
            } else {
                this.$toasted.error('One or more required fields are empty.')
            }
        },
        replacer (name, value) {
            if (value === null) {
                return ''
            }
            return value
        },
    },
}
</script>
