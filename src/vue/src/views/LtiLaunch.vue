<template>
    <content-single-column>
        <h1
            v-if="currentPage"
            class="theme-h1 mb-2"
        >
            {{ currentPage }}
        </h1>
        <b-card
            v-if="currentPage"
        >
            <lti-create-link-course
                v-if="handleCourseChoice"
                :lti="lti"
                :courses="courses"
                @handleAction="handleActions"
            />
            <lti-create-link-assignment
                v-else-if="handleAssignmentChoice"
                :lti="lti"
                :page="page"
                :linkableAssignments="linkableAssignments ? linkableAssignments : []"
                @handleAction="handleActions"
            />
        </b-card>
        <load-spinner
            v-else
            class="mt-5"
        />
    </content-single-column>
</template>

<script>
import assignmentAPI from '@/api/assignment.js'
import contentSingleColumn from '@/components/columns/ContentSingleColumn.vue'
import courseAPI from '@/api/course.js'
import loadSpinner from '@/components/loading/LoadSpinner.vue'
import ltiAPI from '@/api/lti.js'
import ltiCreateLinkAssignment from '@/components/lti/LtiCreateLinkAssignment.vue'
import ltiCreateLinkCourse from '@/components/lti/LtiCreateLinkCourse.vue'
import router from '@/router/index.js'

export default {
    name: 'LtiLaunch',
    components: {
        contentSingleColumn,
        loadSpinner,
        ltiCreateLinkCourse,
        ltiCreateLinkAssignment,
    },
    data () {
        return {
            currentPage: '',

            /* Variables for loading the right component. */
            handleCourseChoice: false,
            handleAssignmentChoice: false,
            ltiJWT: '',
            canAutoSetupState: '',

            /* Possible states for the control flow. */
            states: {
                state: '',

                /* Extern variables for checking the state of the lti launch. */
                lacking_permissions_to_setup_assignment: '-4',
                lacking_permissions_to_setup_course: '-3',

                bad_auth: '-1',
                no_course: '0',
                no_assign: '1',
                new_course: '2',
                new_assign: '3',
                finish_t: '4',
                finish_s: '5',
                grade_center: '6',

                /* Intern variables for checking the state of the lti launch. */
                check_assign: '7',
            },

            /* Set a dictionary with the needed lti variables. */
            lti: {
                ltiCourseID: '',
                ltiCourseName: '',
                ltiCourseAbbr: '',
                ltiCourseStart: '',
                ltiAssignName: '',
                ltiAssignID: '',
                ltiAssignPublished: '',
                ltiPointsPossible: '',
                ltiAssignUnlock: '',
                ltiAssignDue: '',
                ltiAssignLock: '',
            },

            /* Set a dictionary with the variables of the linked page. */
            page: {
                cID: '',
                aID: '',
                jID: '',
            },

            courses: null,
            assignments: null,
            linkableAssignments: null,
        }
    },
    watch: {
        'states.state': function (val) { // eslint-disable-line
            this.updateState(val)
        },
    },
    mounted () {
        this.ltiJWT = this.$route.query.ltiJWT

        ltiAPI.getLtiParams(this.ltiJWT).then((response) => {
            if (response.state === this.states.lacking_permissions_to_setup_course
                || (response.state === this.states.lacking_permissions_to_setup_assignment)) {
                this.$router.push({
                    name: 'NotSetup',
                    params: {
                        courseName: response.lti_cName,
                        assignmentName: response.lti_aName,
                        ltiState: response.state,
                    },
                })
            } else if (response.state === this.states.bad_auth) {
                this.$store.commit('sentry/CAPTURE_SCOPED_MESSAGE', {
                    msg: 'Invalid credentials from the LTI environment',
                    extra: { response },
                    tags: { lti: response.state },
                })
                router.push({
                    name: 'ErrorPage',
                    params: {
                        code: '511',
                        reasonPhrase: 'Network authorization required',
                        description: `Invalid credentials from the LTI environment.
                                      Please contact the system administrator.`,
                    },
                })
            }

            this.lti.ltiCourseName = response.lti_cName
            this.lti.ltiCourseAbbr = response.lti_abbr
            this.lti.ltiCourseID = response.lti_cID
            this.lti.ltiCourseStart = response.lti_course_start
            this.lti.ltiAssignName = response.lti_aName
            this.lti.ltiAssignID = response.lti_aID
            this.lti.ltiPointsPossible = response.lti_points_possible
            this.lti.ltiAssignUnlock = response.lti_aUnlock
            this.lti.ltiAssignDue = response.lti_aDue
            this.lti.ltiAssignLock = response.lti_aLock
            this.lti.ltiAssignPublished = response.lti_aPublished
            this.page.cID = response.cID
            this.page.aID = response.aID
            this.page.jID = response.jID
            this.canAutoSetupState = response.state

            /* The lti parameters such as course id are not set if we are a student. */
            if (this.lti.ltiCourseID) {
                courseAPI.getLinkable().then((courses) => {
                    if (courses.length) {
                        this.courses = courses
                        this.states.state = this.canAutoSetupState
                    } else {
                        this.autoSetupCourse()
                    }
                })
            } else {
                this.states.state = this.canAutoSetupState
            }
        })
    },
    methods: {
        autoSetupCourse () {
            courseAPI.create({
                name: this.lti.ltiCourseName,
                abbreviation: this.lti.ltiCourseAbbr,
                startdate: this.lti.ltiCourseStart.split(' ')[0] || '',
                enddate: '',
                lti_id: this.lti.ltiCourseID,
            }).then((course) => {
                this.page.cID = course.id
                this.updateState(this.states.new_assign)
            })
        },
        autoSetupAssignment () {
            assignmentAPI.create({
                name: this.lti.ltiAssignName,
                description: '',
                course_id: this.page.cID,
                lti_id: this.lti.ltiAssignID,
                points_possible: this.lti.ltiPointsPossible,
                unlock_date: this.lti.ltiAssignUnlock.slice(0, -9),
                due_date: this.lti.ltiAssignDue.slice(0, -9),
                lock_date: this.lti.ltiAssignLock.slice(0, -9),
                is_published: this.lti.ltiAssignPublished,
            }).then((assignment) => {
                this.page.aID = assignment.id
                this.updateState(this.states.finish_t)
            })
        },
        handleActions (args) {
            switch (args[0]) {
            case 'courseCreated':
                this.handleCourseChoice = false
                this.page.cID = args[1]
                this.$toasted.success('Course Created!')
                ltiAPI.updateLtiGroups(this.ltiJWT)
                this.states.state = this.states.check_assign
                break
            case 'courseLinked':
                this.handleCourseChoice = false
                this.page.cID = args[1]
                this.$toasted.success('Course Linked!')
                ltiAPI.updateLtiGroups(this.ltiJWT)
                this.states.state = this.states.check_assign
                break
            case 'assignmentIntegrated':
                this.handleAssignmentChoice = false
                this.page.aID = args[1]
                this.$toasted.success('Assignment Linked!')
                this.states.state = this.states.finish_t
                break
            case 'assignmentCreated':
                this.page.aID = args[1]
                this.$toasted.success('Assignment Created!')
                this.states.state = this.states.finish_t
                break
            default:
                throw Error(`Unknown argument encountered: ${args[0]}`)
            }
        },
        updateState (state) {
            this.currentPage = ''

            switch (state) {
            case this.states.new_course:
                this.currentPage = 'Course setup'
                this.handleCourseChoice = true
                break
            case this.states.new_assign:
                assignmentAPI.getImportable().then((assignments) => {
                    this.assignments = assignments
                    this.linkableAssignments = assignments.slice()
                    for (let i = 0; i < this.linkableAssignments.length; i++) {
                        this.linkableAssignments[i].assignments = this.linkableAssignments[i].assignments.filter(
                            (assignment) => !assignment.active_lti_course
                            || assignment.active_lti_course.cID !== this.page.cID)
                    }
                    if (this.assignments.length) {
                        this.currentPage = 'Assignment setup'
                        this.handleAssignmentChoice = true
                    } else {
                        this.autoSetupAssignment()
                    }
                })
                break
            case this.states.check_assign:
                assignmentAPI.getWithLti(this.lti.ltiAssignID, { redirect: false, customErrorToast: '' })
                    .then((assignment) => {
                        if (assignment === undefined) {
                            this.states.state = this.states.new_assign
                        } else {
                            this.page.aID = assignment.id
                            this.states.state = this.states.finish_t
                        }
                    })
                    .catch((error) => {
                        if (error.response.status === 404) {
                            this.states.state = this.states.new_assign
                        }
                    })
                break
            case this.states.grade_center:
                this.$router.push({
                    name: 'Journal',
                    params: {
                        cID: this.page.cID,
                        aID: this.page.aID,
                        jID: this.page.jID,
                    },
                })
                break
            case this.states.finish_s:
                /* Student has created a journal for an existing assignment, we need to update the store. */
                this.$store.dispatch('user/populateStore').then(() => {
                    /* If journal id is not set, it is a group assignment, and it should go to JoinJournal. */
                    if (this.page.jID !== null) {
                        this.$router.push({
                            name: 'Journal',
                            params: {
                                cID: this.page.cID,
                                aID: this.page.aID,
                                jID: this.page.jID,
                            },
                        })
                    } else {
                        this.$router.push({
                            name: 'JoinJournal',
                            params: {
                                cID: this.page.cID,
                                aID: this.page.aID,
                            },
                        })
                    }
                }, (error) => {
                    this.$router.push({
                        name: 'ErrorPage',
                        params: {
                            code: error.response.status,
                            reasonPhrase: error.response.statusText,
                            description: 'Unable to acquire the newly created journal data, please try again.',
                        },
                    })
                })
                break
            case this.states.finish_t:
                /* Teacher might have created or linked a new course and or assignment, we need to update the store. */
                this.$store.dispatch('user/populateStore').then(() => {
                    if (this.canAutoSetupState === this.states.finish_t) {
                        /* The assignment already existed. */
                        this.$router.push({
                            name: 'Assignment',
                            params: {
                                cID: this.page.cID,
                                aID: this.page.aID,
                            },
                        })
                    } else {
                        /* A new assignment has been created, yet to be configured. */
                        this.$router.push({
                            name: 'AssignmentEditor',
                            params: {
                                cID: this.page.cID,
                                aID: this.page.aID,
                            },
                        })
                    }
                }, (error) => {
                    this.$router.push({
                        name: 'ErrorPage',
                        params: {
                            code: error.response.status,
                            reasonPhrase: error.response.statusText,
                            description: 'Unable to acquire the newly created assignment data, please try again.',
                        },
                    })
                })
                break
            default:
                throw Error(`Unknown LTI state encountered: ${state}`)
            }
        },
    },
}
</script>
