<template>
    <div>
        <b-alert
            v-if="!$store.getters['user/verifiedEmail']"
            class="mb-2"
            show
        >
            <b>Warning:</b> Your email address is not verified.
            No notifications are sent until you verify your email address via the 'details' tab above!
        </b-alert>
        <div class="p-2 text-center background-light-grey round-border mb-2">
            <span class="mr-3 ml-3 small d-inline-block">
                <icon
                    name="bell"
                    class="shift-up-3 mr-2"
                />
                As soon as possible
            </span>
            <span class="mr-3 ml-3 small d-inline-block">
                <icon
                    name="clock"
                    class="shift-up-3 mr-2"
                />
                In daily digest
            </span>
            <span class="mr-3 ml-3 small d-inline-block">
                <icon
                    name="calendar"
                    class="shift-up-3 mr-2"
                />
                In weekly digest
            </span>
            <span class="mr-3 ml-3 small d-inline-block">
                <icon
                    name="times"
                    class="shift-up-3 mr-2"
                />
                Disabled
            </span>
        </div>
        <b-table-simple
            responsive
            :class="{
                'input-disabled': !$store.getters['user/verifiedEmail']
            }"
            class="mb-0 no-top-table-border round-border"
        >
            <b-tbody>
                <b-tr>
                    <b-td>
                        Receive notifications from<br/>
                        <span class="small">
                            Only receive notifications for groups which you are also a member of.
                        </span>
                    </b-td>
                    <b-td>
                        <b-button
                            v-if="$store.getters['preferences/saved'].group_only_notifications"
                            class="float-right"
                            @click.stop
                            @click="$store.commit(
                                'preferences/CHANGE_PREFERENCES', { group_only_notifications: false })"
                        >
                            <icon name="user-friends"/>
                            Own Groups
                        </b-button>
                        <b-button
                            v-else
                            class="float-right"
                            @click.stop
                            @click="$store.commit('preferences/CHANGE_PREFERENCES', { group_only_notifications: true })"
                        >
                            <icon name="users"/>
                            All Users
                        </b-button>
                    </b-td>
                </b-tr>
                <b-tr
                    v-for="(preference, i) in reminderPreferences"
                    :key="`notification-reminder-preferences-${i}`"
                >
                    <b-td :title="preference.name">
                        {{ preference.name }}<br/>
                        <span class="small">
                            {{ preference.description }}
                        </span>
                    </b-td>
                    <b-td>
                        <radio-button
                            v-model="$store.getters['preferences/saved'][preference['key']]"
                            :options="[
                                {
                                    value: 'p',
                                    icon: 'bell',
                                    class: 'green-button',
                                },
                                {
                                    value: 'd',
                                    icon: 'clock',
                                    class: 'green-button',
                                },
                                {
                                    value: 'w',
                                    icon: 'calendar',
                                    class: 'green-button',
                                },
                                {
                                    value: 'o',
                                    icon: 'times',
                                    class: 'red-button',
                                },
                            ]"
                            class="float-right"
                            @input="e => changePreference(preference['key'], e)"
                        />
                    </b-td>
                </b-tr>
                <b-tr
                    v-for="(preference, i) in notificationPreferences"
                    :key="`notification-preferences-${i}`"
                >
                    <b-td :title="preference.name">
                        {{ preference.name }}<br/>
                        <span class="small">
                            {{ preference.description }}
                        </span>
                    </b-td>
                    <b-td>
                        <radio-button
                            v-model="$store.getters['preferences/saved'][preference['key']]"
                            :options="[
                                {
                                    value: 'p',
                                    icon: 'bell',
                                    class: 'green-button',
                                },
                                {
                                    value: 'd',
                                    icon: 'clock',
                                    class: 'green-button',
                                },
                                {
                                    value: 'w',
                                    icon: 'calendar',
                                    class: 'green-button',
                                },
                                {
                                    value: 'o',
                                    icon: 'times',
                                    class: 'red-button',
                                },
                            ]"
                            class="float-right"
                            @input="e => changePreference(preference['key'], e)"
                        />
                    </b-td>
                </b-tr>
            </b-tbody>
        </b-table-simple>
    </div>
</template>

<script>
import RadioButton from '@/components/assets/RadioButton.vue'

export default {
    components: {
        RadioButton,
    },
    data () {
        return {
            notificationPreferences: [
                {
                    name: 'New courses',
                    key: 'new_course_notifications',
                    description: 'Receive an email when you are added to a new course.',
                },
                {
                    name: 'New assignments',
                    key: 'new_assignment_notifications',
                    description: 'Receive an email when a new assignment is published.',
                },
                {
                    name: 'Journal updates',
                    key: 'new_node_notifications',
                    description: 'Receive an email when a new deadline is added to your journal.',
                },
                {
                    name: 'New entries',
                    key: 'new_entry_notifications',
                    description: 'Receive an email when a new entry is posted.',
                },
                {
                    name: 'Grade updates',
                    key: 'new_grade_notifications',
                    description: 'Receive an email when you receive a grade.',
                },
                {
                    name: 'New comments',
                    key: 'new_comment_notifications',
                    description: 'Receive an email when a new comment is posted.',
                },
                {
                    name: 'New journal import requests',
                    key: 'new_journal_import_request_notifications',
                    description: 'Receive an email when a student wants to import the entries from an older journal.',
                },
            ],
            reminderPreferences: [
                {
                    name: 'Deadline reminders',
                    key: 'upcoming_deadline_reminder',
                    description: 'Receive an email one day and/or one week in advance of an unfinished deadline.',
                },
            ],
        }
    },
    methods: {
        changePreference (key, value) {
            const toUpdate = {}
            toUpdate[key] = value
            this.$store.commit('preferences/CHANGE_PREFERENCES', toUpdate)
        },
    },
}
</script>
