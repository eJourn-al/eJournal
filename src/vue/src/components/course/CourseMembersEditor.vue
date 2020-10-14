<template>
    <div>
        <h4 class="theme-h4 mb-2">
            <span>Manage course members</span>
        </h4>
        <div class="d-flex">
            <input
                v-if="viewEnrolled"
                v-model="searchValue"
                class="theme-input flex-grow-1 no-width multi-form mr-2"
                type="text"
                placeholder="Search..."
            />
            <input
                v-if="!viewEnrolled"
                v-model="unenrolledQuery"
                class="theme-input flex-grow-1 no-width multi-form mr-2"
                type="text"
                placeholder="Name or username with at least 5 characters"
                @keyup.enter="searchUnenrolled"
            />
            <b-button
                v-if="!viewEnrolled"
                class="multi-form mr-2"
                @click="searchUnenrolled"
            >
                <icon name="search"/>
                Search users
            </b-button>
            <b-button
                v-if="viewEnrolled"
                class="multi-form"
                @click.stop
                @click="toggleEnrolled"
            >
                <icon name="users"/>
                Enrolled
            </b-button>
            <b-button
                v-if="!viewEnrolled"
                class="multi-form"
                @click.stop
                @click="toggleEnrolled"
            >
                <icon name="user-plus"/>
                Unenrolled
            </b-button>
        </div>
        <div class="d-flex">
            <b-form-select
                v-model="selectedSortOption"
                :selectSize="1"
                class="theme-select multi-form mr-2"
            >
                <option value="name">
                    Sort by name
                </option>
                <option value="username">
                    Sort by username
                </option>
            </b-form-select>
            <b-form-select
                v-model="groupFilter"
                :selectSize="1"
                class="theme-select multi-form mr-2"
            >
                <option :value="null">
                    Filter on group...
                </option>
                <option
                    v-for="group in groups"
                    :key="group.name"
                    :value="group.name"
                >
                    {{ group.name }}
                </option>
            </b-form-select>
            <b-button
                v-if="!order"
                class="multi-form"
                @click.stop
                @click="setOrder(!order)"
            >
                <icon name="long-arrow-alt-down"/>
                Ascending
            </b-button>
            <b-button
                v-if="order"
                class="multi-form"
                @click.stop
                @click="setOrder(!order)"
            >
                <icon name="long-arrow-alt-up"/>
                Descending
            </b-button>
        </div>
        <b-card
            v-if="!viewEnrolled && !unenrolledStudents.length"
            class="no-hover"
        >
            <div class="float-left">
                <b>{{ unenrolledQueryDescription }}</b>
            </div>
        </b-card>

        <div v-if="viewEnrolled">
            <course-participant-card
                v-for="p in filteredUsers"
                :key="p.id"
                :cID="course.id"
                :group.sync="p.group"
                :groups="groups"
                :user="p"
                :numTeachers="numTeachers"
                :roles="roles"
                @delete-participant="deleteParticipantLocally"
                @update-participants="updateParticipants"
            />
        </div>
        <div v-else>
            <add-user-card
                v-for="p in filteredUsers"
                :key="p.id"
                :cID="course.id"
                :user="p"
                @add-participant="addParticipantLocally"
            />
        </div>
    </div>
</template>

<script>
import addUsersToCourseCard from '@/components/course/AddUsersToCourseCard.vue'
import courseParticipantCard from '@/components/course/CourseParticipantCard.vue'

import participationAPI from '@/api/participation.js'
import roleAPI from '@/api/role.js'
import groupAPI from '@/api/group.js'

import { mapGetters, mapMutations } from 'vuex'

export default {
    name: 'CourseEdit',
    components: {
        'add-user-card': addUsersToCourseCard,
        'course-participant-card': courseParticipantCard,
    },
    props: {
        course: {
            required: true,
        },
    },
    data () {
        return {
            participants: [],
            unenrolledStudents: [],
            groups: [],
            unenrolledLoaded: false,
            numTeachers: 0,
            roles: [],
            unenrolledQuery: '',
            unenrolledQueryDescription: 'Search unenrolled users in the search field above.',
        }
    },
    computed: {
        ...mapGetters({
            order: 'preferences/courseMembersSortAscending',
            viewEnrolled: 'preferences/courseMembersViewEnrolled',
            getCourseMembersGroupFilter: 'preferences/courseMembersGroupFilter',
            getCourseMembersSearchValue: 'preferences/courseMembersSearchValue',
            getCourseMembersSortBy: 'preferences/courseMembersSortBy',
        }),
        selectedSortOption: {
            get () {
                return this.getCourseMembersSortBy
            },
            set (value) {
                this.setCourseMembersSortBy(value)
            },
        },
        searchValue: {
            get () {
                return this.getCourseMembersSearchValue
            },
            set (value) {
                this.setCourseMembersSearchValue(value)
            },
        },
        groupFilter: {
            get () {
                return this.getCourseMembersGroupFilter
            },
            set (value) {
                this.setCourseMembersGroupFilter(value)
            },
        },
        filteredUsers () {
            const self = this

            function compareFullName (a, b) {
                return self.compare(a.full_name, b.full_name)
            }

            function compareUsername (a, b) {
                return self.compare(a.username, b.username)
            }

            function searchFilter (user) {
                const username = user.username.toLowerCase()
                const fullName = user.full_name.toLowerCase()
                const searchValue = self.getCourseMembersSearchValue.toLowerCase()

                return username.includes(searchValue)
                    || fullName.includes(searchValue)
            }

            function groupFilter (user) {
                /* Only apply group filter is view enrolled. */
                if (self.viewEnrolled) {
                    /* If student has no groups, return false. */
                    if (!user.groups) {
                        return false
                    }
                    /* Only check if group filter is applied. */
                    if (self.groupFilter) {
                        return user.groups.map(group => group.name).includes(self.groupFilter)
                    }
                }
                return true
            }

            let viewList = this.participants

            /* Switch view list with drop down menu and load unenrolled
               students when accessing other students at first time. */
            if (!this.viewEnrolled) {
                viewList = this.unenrolledStudents
            }

            /* Filter list based on search input. */
            if (this.selectedSortOption === 'name') {
                viewList = viewList.sort(compareFullName)
            } else if (this.selectedSortOption === 'username') {
                viewList = viewList.sort(compareUsername)
            }

            return viewList.filter(searchFilter).filter(groupFilter)
        },
    },
    watch: {
        participants: {
            handler (val) {
                this.numTeachers = val.filter(p => p.role === 'Teacher').length
            },
            deep: true,
        },
    },
    created () {
        participationAPI.getEnrolled(this.course.id)
            .then((users) => { this.participants = users })
        roleAPI.getFromCourse(this.course.id)
            .then((roles) => { this.roles = roles })
        groupAPI.getAllFromCourse(this.course.id)
            .then((groups) => { this.groups = groups })
    },
    methods: {
        ...mapMutations({
            setOrder: 'preferences/SET_COURSE_MEMBERS_SORT_ASCENDING',
            setViewEnrolled: 'preferences/SET_COURSE_MEMBERS_VIEW_ENROLLED',
            setCourseMembersGroupFilter: 'preferences/SET_COURSE_MEMBERS_GROUP_FILTER',
            setCourseMembersSearchValue: 'preferences/SET_COURSE_MEMBERS_SEARCH_VALUE',
            setCourseMembersSortBy: 'preferences/SET_COURSE_MEMBERS_SORT_BY',
        }),
        compare (a, b) {
            if (a < b) { return this.order ? 1 : -1 }
            if (a > b) { return this.order ? -1 : 1 }
            return 0
        },

        deleteParticipantLocally (user) {
            this.participants = this.participants.filter(item => user.id !== item.id)
        },
        addParticipantLocally (user) {
            this.unenrolledStudents = this.unenrolledStudents.filter(item => user.id !== item.id)
            user.role = 'Student'
            user.group = null
            this.participants.push(user)
        },

        updateParticipants (val, uID) {
            for (let i = 0; i < this.participants.length; i++) {
                if (uID === this.participants[i].id) {
                    this.participants[i].role = val
                }
            }
            this.numTeachers = this.participants.filter(p => p.role === 'Teacher').length
        },

        toggleEnrolled () {
            this.setViewEnrolled(!this.viewEnrolled)
            this.unenrolledStudents = []
            this.unenrolledQuery = ''
            this.unenrolledQueryDescription = 'Search unenrolled users in the search field above.'
        },

        searchUnenrolled () {
            this.unenrolledQuery = this.unenrolledQuery.trim()
            participationAPI.getUnenrolled(this.course.id, this.unenrolledQuery)
                .then((users) => {
                    this.unenrolledStudents = users
                    if (!this.unenrolledStudents.length) {
                        if (this.unenrolledQuery.length < 5) {
                            const desc = 'No exact match found. To search for users, provide at least 5 characters.'
                            this.unenrolledQueryDescription = desc
                        } else {
                            this.unenrolledQueryDescription = 'No users found.'
                        }
                    }
                })
        },
    },
}
</script>
