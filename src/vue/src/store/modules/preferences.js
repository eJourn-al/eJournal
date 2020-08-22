import preferencesAPI from '@/api/preferences.js'
import store from '@/store'
import * as types from '../constants/mutation-types.js'
import * as preferenceOptions from '../constants/preference-types.js'

const getters = {
    // Stored user preferences.
    saved: state => state.saved,

    // Search filters.
    todoSortBy: state => state.todo.sortBy,
    todoFilterOwnGroups: state => state.todo.filterOwnGroups,
    journalSortAscending: state => state.journal.sortAscending,
    journalGroupFilter: state => state.journal.groupFilter,
    journalSelfSetGroupFilter: state => state.journal.selfSetGroupFilter,
    journalSearchValue: state => state.journal.searchValue,
    journalSortBy: state => state.journal.sortBy,
    journalAID: state => state.journal.aID,
    courseMembersSortAscending: state => state.courseMembers.sortAscending,
    courseMembersViewEnrolled: state => state.courseMembers.viewEnrolled,
    courseMembersGroupFilter: state => state.courseMembers.groupFilter,
    courseMembersSearchValue: state => state.courseMembers.searchValue,
    courseMembersSortBy: state => state.courseMembers.sortBy,
    assignmentOverviewSortAscending: state => state.assignmentOverview.sortAscending,
    assignmentOverviewSearchValue: state => state.assignmentOverview.searchValue,
    assignmentOverviewSortBy: state => state.assignmentOverview.sortBy,
    assignmentOverviewFilterOwnGroups: state => state.assignmentOverview.filterOwnGroups,
}

const mutations = {
    [types.HYDRATE_PREFERENCES] (state, preferences) {
        state.saved = preferences
    },
    [types.CHANGE_PREFERENCES] (state, preferences) {
        const responseSuccessToast = !Object.keys(preferences).some(key => [
            'hide_version_alert',
            'grade_button_setting',
            'comment_button_setting',
        ].includes(key))
        preferencesAPI.update(
            store.getters['user/uID'],
            preferences,
            { responseSuccessToast },
        ).then(
            Object.keys(preferences).forEach((key) => {
                if (key in state.saved) {
                    state.saved[key] = preferences[key]
                }
            }),
        )
    },
    [types.SET_TODO_SORT_BY] (state, sortByOption) {
        if (!preferenceOptions.TODO_SORT_OPTIONS.has(sortByOption)) { throw new Error('Invalid TODO sorting option.') }
        state.todo.sortBy = sortByOption
    },
    [types.SET_TODO_FILTER_OWN_GROUPS] (state, filterOwnGroups) {
        state.todo.filterOwnGroups = filterOwnGroups
    },
    [types.SET_JOURNAL_SORT_ASCENDING] (state, sortAscending) {
        state.journal.sortAscending = sortAscending
    },
    [types.SET_JOURNAL_GROUP_FILTER] (state, groupFilter) {
        state.journal.groupFilter = groupFilter
    },
    [types.SET_JOURNAL_SELF_SET_GROUP_FILTER] (state, selfSet) {
        state.journal.selfSetGroupFilter = selfSet
    },
    [types.SET_JOURNAL_SEARCH_VALUE] (state, searchValue) {
        state.journal.searchValue = searchValue
    },
    [types.SET_JOURNAL_SORT_BY] (state, sortByOption) {
        if (!preferenceOptions.JOURNAL_SORT_OPTIONS.has(sortByOption)) {
            throw new Error('Invalid journal sorting option.')
        }
        state.journal.sortBy = sortByOption
    },
    [types.SWITCH_JOURNAL_ASSIGNMENT] (state, aID) {
        if (aID !== state.journal.aID) {
            state.journal.aID = aID
            state.journal.sortAscending = true
            state.journal.groupFilter = null
            state.journal.selfSetGroupFilter = false
            state.journal.searchValue = ''
            state.journal.sortBy = 'markingNeeded'
        }
    },
    [types.SET_COURSE_MEMBERS_SORT_ASCENDING] (state, sortAscending) {
        state.courseMembers.sortAscending = sortAscending
    },
    [types.SET_COURSE_MEMBERS_VIEW_ENROLLED] (state, viewEnrolled) {
        state.courseMembers.viewEnrolled = viewEnrolled
    },
    [types.SET_COURSE_MEMBERS_GROUP_FILTER] (state, groupFilter) {
        state.courseMembers.groupFilter = groupFilter
    },
    [types.SET_COURSE_MEMBERS_SEARCH_VALUE] (state, searchValue) {
        state.courseMembers.searchValue = searchValue
    },
    [types.SET_COURSE_MEMBERS_SORT_BY] (state, sortByOption) {
        if (!preferenceOptions.COURSE_MEMBER_SORT_OPTIONS.has(sortByOption)) {
            throw new Error('Invalid course member sorting option.')
        }
        state.courseMembers.sortBy = sortByOption
    },
    [types.SET_ASSIGNMENT_OVERVIEW_SORT_ASCENDING] (state, sortAscending) {
        state.assignmentOverview.sortAscending = sortAscending
    },
    [types.SET_ASSIGNMENT_OVERVIEW_SEARCH_VALUE] (state, searchValue) {
        state.assignmentOverview.searchValue = searchValue
    },
    [types.SET_ASSIGNMENT_OVERVIEW_SORT_BY] (state, sortByOption) {
        if (!preferenceOptions.ASSIGNMENT_OVERVIEW_SORT_OPTIONS.has(sortByOption)) {
            throw new Error('Invalid assignment overview sorting option.')
        }
        state.assignmentOverview.sortBy = sortByOption
    },
    [types.SET_ASSIGNMENT_OVERVIEW_FILTER_OWN_GROUPS] (state, filterOwnGroups) {
        state.assignmentOverview.filterOwnGroups = filterOwnGroups
    },
    [types.RESET_PREFERENCES] (state) {
        state.saved = {}
        state.todo.sortBy = 'date'
        state.todo.filterOwnGroups = true
        state.journal.aID = null
        state.journal.sortAscending = true
        state.journal.groupFilter = null
        state.journal.selfSetGroupFilter = false
        state.journal.searchValue = ''
        state.journal.sortBy = 'markingNeeded'
        state.courseMembers.sortAscending = true
        state.courseMembers.viewEnrolled = true
        state.courseMembers.groupFilter = null
        state.courseMembers.searchValue = ''
        state.courseMembers.sortBy = 'name'
        state.assignmentOverview.sortAscending = true
        state.assignmentOverview.searchValue = ''
        state.assignmentOverview.sortBy = 'name'
        state.assignmentOverview.filterOwnGroups = true
    },
}

export default {
    namespaced: true,
    state: {
        saved: {},
        todo: {
            sortBy: 'date',
            filterOwnGroups: true,
        },
        journal: {
            aID: null,
            sortAscending: true,
            groupFilter: null,
            selfSetGroupFilter: false,
            searchValue: '',
            sortBy: 'markingNeeded',
        },
        courseMembers: {
            sortAscending: true,
            viewEnrolled: true,
            groupFilter: null,
            searchValue: '',
            sortBy: 'name',
        },
        assignmentOverview: {
            sortAscending: true,
            searchValue: '',
            sortBy: 'name',
            filterOwnGroups: true,
        },
    },
    getters,
    mutations,
}
