<template>
    <div>
        <h4 class="theme-h4 mb-2 mt-4">
            <span>Email notifications</span>
        </h4>

        <b-card
            :class="$root.getBorderClass($route.params.uID)"
            class="no-hover multi-form"
        >
            <b-row>
                <b-col
                    xs="3"
                    class="text-center"
                >
                    <icon
                        name="bell"
                        class="fill-grey shift-up-3 mr-1"
                    />
                    Day and week before
                </b-col>
                <b-col
                    xs="3"
                    class="text-center"
                >
                    <icon
                        name="clock"
                        class="fill-grey shift-up-3 mr-1"
                    />
                    Day before
                </b-col>
                <b-col
                    xs="3"
                    class="text-center"
                >
                    <icon
                        name="calendar"
                        class="fill-grey shift-up-3 mr-1"
                    />
                    Week before
                </b-col>
                <b-col
                    xs="3"
                    class="text-center"
                >
                    <icon
                        name="times"
                        class="fill-grey shift-up-3 mr-1"
                    />
                    No reminders
                </b-col>
            </b-row>
            <hr/>
            <div
                v-for="preference in reminderPreferences"
                :key="preference['key']"
                class="clearfix mt-2"
            >
                <radio-button
                    v-model="$store.getters['preferences/saved'][preference['key']]"
                    :options="[
                        {
                            value: 'p',
                            icon: 'bell',
                            class: 'add-button',
                        },
                        {
                            value: 'd',
                            icon: 'clock',
                            class: 'add-button',
                        },
                        {
                            value: 'w',
                            icon: 'calendar',
                            class: 'add-button',
                        },
                        {
                            value: 'o',
                            icon: 'times',
                            class: 'delete-button',
                        },
                    ]"
                    class="float-right"
                    @input="e => changePreference(preference['key'], e)"
                />
                <h2 class="theme-h2 field-heading multi-form">
                    {{ preference['name'] }}
                    <tooltip
                        :tip="preference['tooltip']"
                    />
                </h2>
            </div>
        </b-card>
        <b-card
            :class="$root.getBorderClass($route.params.uID)"
            class="no-hover multi-form"
        >
            <b-row>
                <b-col
                    xs="3"
                    class="text-center"
                >
                    <icon
                        name="bell"
                        class="fill-grey shift-up-3 mr-1"
                    />
                    Immediately
                </b-col>
                <b-col
                    xs="3"
                    class="text-center"
                >
                    <icon
                        name="clock"
                        class="fill-grey shift-up-3 mr-1"
                    />
                    Daily digest
                </b-col>
                <b-col
                    xs="3"
                    class="text-center"
                >
                    <icon
                        name="calendar"
                        class="fill-grey shift-up-3 mr-1"
                    />
                    Weekly digest
                </b-col>
                <b-col
                    xs="3"
                    class="text-center"
                >
                    <icon
                        name="times"
                        class="fill-grey shift-up-3 mr-1"
                    />
                    No notifications
                </b-col>
            </b-row>
            <hr/>
            <div
                v-for="preference in notificationPreferences"
                :key="preference['key']"
                class="clearfix mt-2"
            >
                <radio-button
                    v-model="$store.getters['preferences/saved'][preference['key']]"
                    :options="[
                        {
                            value: 'p',
                            icon: 'bell',
                            class: 'add-button',
                        },
                        {
                            value: 'd',
                            icon: 'clock',
                            class: 'add-button',
                        },
                        {
                            value: 'w',
                            icon: 'calendar',
                            class: 'add-button',
                        },
                        {
                            value: 'o',
                            icon: 'times',
                            class: 'delete-button',
                        },
                    ]"
                    class="float-right"
                    @input="e => changePreference(preference['key'], e)"
                />
                <h2 class="theme-h2 field-heading multi-form">
                    {{ preference['name'] }}
                    <tooltip
                        :tip="preference['tooltip']"
                    />
                </h2>
            </div>
            <hr/>
            <div class="clearfix">
                <b-button
                    v-if="$store.getters['preferences/saved'].group_only_notifications"
                    class="float-right"
                    @click.stop
                    @click="$store.commit('preferences/CHANGE_PREFERENCES', { group_only_notifications: false })"
                >
                    <icon name="user-friends"/>
                    Your Groups
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
                <h2 class="theme-h2 field-heading multi-form">
                    Receive notifications from
                    <tooltip
                        tip="Only get notifications of people that are in groups that you are also in"
                    />
                </h2>
            </div>
        </b-card>
    </div>
</template>

<script>
import RadioButton from '@/components/assets/RadioButton.vue'
import tooltip from '@/components/assets/Tooltip.vue'

export default {
    components: {
        RadioButton,
        tooltip,
    },
    props: ['userData'],
    data () {
        return {
            notificationPreferences: [
                {
                    name: 'New courses',
                    key: 'new_course_notifications',
                    tooltip: 'Receive an email when you are added to a new course.',
                },
                {
                    name: 'New assignments',
                    key: 'new_assignment_notifications',
                    tooltip: 'Receive an email when a new assignment is published.',
                },
                {
                    name: 'Journal updates',
                    key: 'new_node_notifications',
                    tooltip: 'Receive an email when a new deadline is added to your journal.',
                },
                {
                    name: 'New entries',
                    key: 'new_entry_notifications',
                    tooltip: 'Receive an email when a new entry is posted.',
                },
                {
                    name: 'Grade updates',
                    key: 'new_grade_notifications',
                    tooltip: 'Receive an email when you receive a grade.',
                },
                {
                    name: 'New comments',
                    key: 'new_comment_notifications',
                    tooltip: 'Receive an email when a new comment is posted.',
                },
                {
                    name: 'New journal import requests',
                    key: 'new_journal_import_request_notifications',
                    tooltip: 'Receive an email when a student wants to import the entries from an older journal.',
                },
            ],
            reminderPreferences: [
                {
                    name: 'Deadline reminders',
                    key: 'upcoming_deadline_reminder',
                    tooltip: 'Receive an email in advance of an unfinished deadline',
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
