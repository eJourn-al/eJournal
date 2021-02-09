<template>
    <b-card class="no-hover">
        <b-form
            :vModel="form.lti_id"
            @submit.prevent="onSubmit"
            @reset.prevent="onReset"
        >
            <h2 class="theme-h2 field-heading required">
                Course name
            </h2>
            <b-input
                v-model="form.name"
                class="multi-form theme-input"
                placeholder="Course name"
            />
            <h2 class="theme-h2 field-heading required">
                Course abbreviation
            </h2>
            <b-input
                v-model="form.abbreviation"
                class="multi-form theme-input"
                maxlength="10"
                placeholder="Course abbreviation (max 10 characters)"
            />
            <b-row>
                <b-col cols="6">
                    <h2 class="theme-h2 field-heading">
                        Start date
                        <tooltip tip="Start date of the course"/>
                    </h2>
                    <reset-wrapper v-model="form.startdate">
                        <flat-pickr
                            v-model="form.startdate"
                            class="multi-form full-width"
                            :config="startDateConfig"
                        />
                    </reset-wrapper>
                </b-col>
                <b-col cols="6">
                    <h2 class="theme-h2 field-heading">
                        End date
                        <tooltip tip="End date of the course"/>
                    </h2>
                    <reset-wrapper v-model="form.enddate">
                        <flat-pickr
                            v-model="form.enddate"
                            class="multi-form full-width"
                            :config="endDateConfig"
                        />
                    </reset-wrapper>
                </b-col>
            </b-row>
            <hr/>
            <b-button
                class="float-left orange-button"
                type="reset"
            >
                <icon name="undo"/>
                Reset
            </b-button>
            <b-button
                class="float-right green-button"
                type="submit"
            >
                <icon name="plus-square"/>
                Create
            </b-button>
        </b-form>
    </b-card>
</template>

<script>
import commonAPI from '@/api/common.js'
import courseAPI from '@/api/course.js'
import tooltip from '@/components/assets/Tooltip.vue'

export default {
    name: 'CreateCourse',
    components: {
        tooltip,
    },
    props: ['lti'],
    data () {
        return {
            form: {
                name: '',
                abbreviation: '',
                startdate: '',
                enddate: '',
                lti_id: '',
            },
        }
    },
    computed: {
        startDateConfig () {
            const additionalConfig = {}
            if (this.form.enddate) {
                additionalConfig.maxDate = new Date(this.form.enddate)
            }
            return Object.assign({}, additionalConfig, this.$root.flatPickrConfig)
        },
        endDateConfig () {
            const additionalConfig = {}
            if (this.form.startdate) {
                additionalConfig.minDate = new Date(this.form.startdate)
            }
            return Object.assign({}, additionalConfig, this.$root.flatPickrConfig)
        },
    },
    mounted () {
        if (this.lti !== undefined) {
            this.form.name = this.lti.ltiCourseName
            this.form.abbreviation = this.lti.ltiCourseAbbr
            this.form.lti_id = this.lti.ltiCourseID
            this.form.startdate = this.lti.ltiCourseStart.split(' ')[0] || ''
            this.form.enddate = ''
        }
    },
    methods: {
        formFilled () {
            return this.form.name && this.form.abbreviation
        },
        onSubmit () {
            if (this.formFilled()) {
                courseAPI.create(this.form)
                    .then((course) => {
                        if (!this.lti) { // If we are here via LTI a full store update will take place anyway.
                            commonAPI.getPermissions(course.id).then((coursePermissions) => {
                                this.$store.commit(
                                    'user/UPDATE_PERMISSIONS',
                                    { permissions: coursePermissions, key: `course${course.id}` },
                                )
                            })
                        }
                        this.$emit('handleAction', course.id)
                    })
            } else {
                this.$toasted.error('One or more required fields are empty.')
            }
        },
        onReset () {
            this.form.name = ''
            this.form.abbreviation = ''
            this.form.startdate = ''
            this.form.enddate = ''
        },
    },
}
</script>
