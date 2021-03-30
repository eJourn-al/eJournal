<template>
    <div class="members">
        <div class="members-header">
            <div @click="lockJournal">
                <icon
                    v-b-tooltip:hover="`Journal members are ${ journal.locked ? '' : 'not ' }locked, this journal can`
                        + `${ journal.locked ? 'not' : '' } be joined or left${ (assignment.can_lock_journal
                            || $hasPermission('can_manage_journals')) ? ': click to toggle' : ''}`"
                    :name="journal.locked ? 'lock' : 'unlock'"
                    :class="{
                        'unlocked-icon': !journal.locked && (assignment.can_lock_journal
                            || $hasPermission('can_manage_journals')),
                        'trash-icon': journal.locked && (assignment.can_lock_journal
                            || $hasPermission('can_manage_journals'))
                    }"
                    class="lock-members-icon fill-grey"
                />
            </div>
            <b class="member-count">
                Members
                <b
                    v-if="journal.author_limit > 1"
                    class="text-grey"
                >
                    ({{ journal.author_count }}/{{ journal.author_limit }})
                </b>
            </b>
        </div>
        <div
            v-for="author in authors"
            :key="`journal-member-${author.user.id}`"
            class="member"
        >
            <div
                v-if="(author.user.id === $store.getters['user/uID'] && !journal.locked) ||
                    $hasPermission('can_manage_journals')"
                class="float-right"
                @click="$hasPermission('can_manage_journals') ? kickFromJournal(author.user) : leaveJournal()"
            >
                <icon
                    name="sign-out-alt"
                    class="trash-icon"
                />
            </div>
            <b class="max-one-line">
                <b-badge
                    v-if="author.needs_lti_link"
                    v-b-tooltip:hover="'This user has not yet visited the assignment in the LMS (Canvas) yet'"
                    pill
                    class="background-red"
                >
                    <icon
                        name="link"
                        class="fill-white shift-up-2"
                        scale="0.65"
                    />
                    LTI
                </b-badge>
                {{ author.user.full_name }}
            </b>
            <span
                v-if="author.user.username"
                class="max-one-line"
            >
                {{ author.user.username }}
            </span>
        </div>
        <div
            v-if="journal.author_count === 0"
            class="member text-grey"
        >
            No members yet
        </div>
        <div
            v-if="$hasPermission('can_manage_journals') && (journal.author_limit === 0 ||
                journal.author_count < journal.author_limit) && participantsWithoutJournal.length > 0"
            class="d-flex mt-3 full-width"
        >
            <theme-select
                v-model="participantsToAdd"
                label="full_name"
                trackBy="id"
                :options="participantsWithoutJournal"
                :multiple="true"
                :searchable="true"
                :multiSelectText="`user${participantsToAdd &&
                    participantsToAdd.length === 1 ? '' : 's'} selected`"
                placeholder="Select Users"
                class="no-right-radius"
            />
            <b-button
                class="green-button no-left-radius"
                @click="addMembers"
            >
                <icon name="user-plus"/>
                Add
            </b-button>
        </div>
    </div>
</template>

<script>
import assignmentAPI from '@/api/assignment.js'
import journalAPI from '@/api/journal.js'

import { mapGetters } from 'vuex'

export default {
    props: {
        assignment: {
            required: true,
        },
        journal: {
            required: true,
        },
    },
    data () {
        return {
            participantsToAdd: [],
            saveRequestInFlight: false,
            authors: [],
        }
    },
    computed: {
        ...mapGetters({
            participantsWithoutJournal: 'content/assignmentParticipantsWithoutJournal',
        }),
    },
    created () {
        journalAPI.getMembers(this.journal.id).then((authors) => { this.authors = authors })
        if (this.$hasPermission('can_manage_journals')) {
            this.getParticipantsWithoutJournal()
        }
    },
    methods: {
        leaveJournal () {
            if (window.confirm('Are you sure you want to leave this journal?'
                + `${this.journal.author_count === 1 ? ' Since you are the last member of this journal, doing so '
                + 'will reset the journal and remove all its entries. This action cannot be undone.' : ''}`)) {
                journalAPI.leave(this.journal.id)
                    .then(() => {
                        this.$router.push({
                            name: 'JoinJournal',
                            params: {
                                cID: this.assignment.course.id, aID: this.assignment.id,
                            },
                        })
                    })
            }
        },
        kickFromJournal (user) {
            if (window.confirm(`Are you sure you want to remove ${user.full_name} from this journal?`
                + `${this.journal.author_count === 1 ? ' Since they are the last member of this journal, doing so '
                + 'will reset the journal and remove all its entries. This action cannot be undone.' : ''}`)) {
                journalAPI.kick(this.journal.id, user.id, { responseSuccessToast: true })
                    .then(() => {
                        this.getParticipantsWithoutJournal()
                        this.authors = this.authors.filter((author) => author.user.id !== user.id)
                        this.journal.author_count = this.authors.length
                        this.journal.usernames = this.authors.map((author) => author.user.username).join(', ')
                        if (this.journal.author_count === 0 && this.$router.app.$route.name !== 'Assignment') {
                            this.$router.push(this.$root.assignmentRoute(this.assignment))
                        }
                    })
            }
        },
        lockJournal () {
            if (this.assignment.can_lock_journal || this.$hasPermission('can_manage_journals')) {
                journalAPI.lock(this.journal.id, !this.journal.locked, { responseSuccessToast: true })
                    .then(() => {
                        this.journal.locked = !this.journal.locked
                    })
            }
        },
        getParticipantsWithoutJournal () {
            assignmentAPI.getParticipantsWithoutJournal(this.assignment.id)
                .then((data) => {
                    this.$store.commit('content/SET_ASSIGNMENT_PARTICIPANTS_WITHOUT_JOURNAL', data)
                })
        },
        addMembers () {
            if (this.journal.author_limit > 1 && this.journal.author_count + this.participantsToAdd.length
                > this.journal.author_limit) {
                this.$toasted.error('Adding these members would exceed this journal\'s member limit.')
            } else if (this.participantsToAdd.length === 0) {
                this.$toasted.error('No users selected.')
            } else {
                this.saveRequestInFlight = true
                const idsToAdd = this.participantsToAdd.reduce((acc, cur) => {
                    acc.push(cur.id)
                    return acc
                }, [])

                journalAPI.addMembers(this.journal.id, idsToAdd)
                    .then((authors) => {
                        this.authors = authors
                        this.journal.author_count = this.authors.length
                        this.journal.usernames = this.authors.map((author) => author.user.username).join(', ')
                        this.saveRequestInFlight = false
                        this.getParticipantsWithoutJournal()
                        this.participantsToAdd = []
                        this.$toasted.success('Successfully added journal members.')
                    })
                    .catch(() => { this.saveRequestInFlight = false })
            }
        },
    },
}
</script>

<style lang="sass">
.members
    .members-header
        border-bottom: 2px solid $theme-dark-grey
    .member
        padding: 5px
        border-bottom: 1px solid $theme-dark-grey
        .trash-icon
            margin-top: 3px
        .max-one-line
            width: calc(100% - 20px)
            .badge
                display: inline-block
                position: relative
                top: -2px
    .lock-members-icon
        float: right
        margin-top: 3px
        margin-right: 9px
        &.unlocked-icon
            margin-right: 4px
        svg
            fill: red
</style>
