<template>
    <load-wrapper :loading="loadingMembers">
        <div class="d-flex">
            <b-input
                v-if="viewEnrolled"
                v-model="searchValue"
                class="flex-grow-1 no-width mb-2 mr-2"
                type="text"
                placeholder="Search..."
            />
            <b-input
                v-if="!viewEnrolled"
                v-model="unenrolledQuery"
                class="flex-grow-1 no-width mb-2 mr-2"
                type="text"
                placeholder="Name or username with at least 5 characters"
                @keyup.enter="searchUnenrolled"
            />
            <b-button
                v-if="!viewEnrolled"
                class="mb-2 mr-2"
                @click="searchUnenrolled"
            >
                <icon name="search"/>
                Search users
            </b-button>
            <b-button
                v-if="viewEnrolled"
                class="mb-2"
                @click.stop
                @click="toggleEnrolled"
            >
                <icon name="users"/>
                Enrolled
            </b-button>
            <b-button
                v-if="!viewEnrolled"
                class="mb-2"
                @click.stop
                @click="toggleEnrolled"
            >
                <icon name="user-plus"/>
                Unenrolled
            </b-button>
        </div>
        <div
            v-if="filteredUsers.length > 0"
            class="d-flex"
        >
            <b-form-select
                v-model="selectedSortOption"
                :selectSize="1"
                class="theme-select mb-2 mr-2"
            >
                <option value="name">
                    Sort by name
                </option>
                <option value="username">
                    Sort by username
                </option>
            </b-form-select>
            <b-form-select
                v-if="viewEnrolled"
                v-model="groupFilter"
                :selectSize="1"
                class="theme-select mb-2 mr-2"
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
                class="mb-2"
                @click.stop
                @click="setOrder(!order)"
            >
                <icon name="long-arrow-alt-down"/>
                Ascending
            </b-button>
            <b-button
                v-if="order"
                class="mb-2"
                @click.stop
                @click="setOrder(!order)"
            >
                <icon name="long-arrow-alt-up"/>
                Descending
            </b-button>
        </div>

        <template v-if="viewEnrolled">
            <course-participant-card
                v-for="p in filteredUsers"
                :key="p.id"
                :cID="cID"
                :group.sync="p.group"
                :groups="groups"
                :user="p"
                :numTeachers="numTeachers"
                :roles="roles"
                @delete-participant="deleteParticipantLocally"
                @update-participants="updateParticipants"
            />
            <not-found
                v-if="filteredUsers.length === 0"
                subject="users"
                explanation="Change the search value."
            />
        </template>
        <template v-else-if="filteredUsers.length > 0">
            <add-user-card
                v-for="p in filteredUsers"
                :key="p.id"
                :cID="cID"
                :user="p"
                @add-participant="addParticipantLocally"
            />
        </template>
        <not-found
            v-else
            subject="users"
            explanation="Change the search value, then press 'Search Users' again."
        />
    </load-wrapper>
</template>

<script>
import AddUsersToCourseCard from '@/components/course/AddUsersToCourseCard.vue'
import CourseParticipantCard from '@/components/course/CourseParticipantCard.vue'
import LoadWrapper from '@/components/loading/LoadWrapper.vue'

import groupAPI from '@/api/group.js'
import participationAPI from '@/api/participation.js'
import roleAPI from '@/api/role.js'

import { mapGetters, mapMutations } from 'vuex'

export default {
    name: 'CourseEdit',
    components: {
        'add-user-card': AddUsersToCourseCard,
        'course-participant-card': CourseParticipantCard,
        LoadWrapper,
    },
    props: {
        cID: {
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
            loadingMembers: true,
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
                        return user.groups.map((group) => group.name).includes(self.groupFilter)
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
                this.numTeachers = val.filter((p) => p.role === 'Teacher').length
            },
            deep: true,
        },
    },
    created () {
        participationAPI.getEnrolled(this.cID)
            .then((users) => {
                this.participants = users
                this.loadingMembers = false
            })
        roleAPI.getFromCourse(this.cID)
            .then((roles) => { this.roles = roles })
        groupAPI.getAllFromCourse(this.cID)
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
            this.participants = this.participants.filter((item) => user.id !== item.id)
        },
        addParticipantLocally (user) {
            this.unenrolledStudents = this.unenrolledStudents.filter((item) => user.id !== item.id)
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
            this.numTeachers = this.participants.filter((p) => p.role === 'Teacher').length
        },

        toggleEnrolled () {
            this.setViewEnrolled(!this.viewEnrolled)
            this.unenrolledStudents = []
            this.unenrolledQuery = ''
            this.unenrolledQueryDescription = 'Search unenrolled users in the search field above.'
        },

        searchUnenrolled () {
            this.unenrolledQuery = this.unenrolledQuery.trim()
            participationAPI.getUnenrolled(this.cID, this.unenrolledQuery)
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
