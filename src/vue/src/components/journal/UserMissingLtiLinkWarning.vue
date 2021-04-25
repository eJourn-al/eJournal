<template>
    <div>
        <b-alert
            v-if="$hasPermission('can_grade')"
            show
        >
            <span v-if="assignment.is_group_assignment">
                <b>Warning:</b> The following journal members have not visited the assignment in the active
                LMS (Canvas) course '{{ assignment.active_lti_course.name }}' yet:
                <ul class="pt-1 pb-1 mb-0">
                    <li
                        v-for="name in journal.needs_lti_link"
                        :key="`lti-author-${name}`"
                    >
                        {{ name }}
                    </li>
                </ul>
                This journal cannot be updated and grades cannot be passed back until each member visits the
                assignment at least once.
            </span>
            <span v-else>
                <b>Warning:</b> This student has not visited the assignment in the active LMS (Canvas)
                course '{{ assignment.active_lti_course.name }}' yet. They cannot update this journal and
                grades cannot be passed back until they visit the assignment at least once.
            </span>
        </b-alert>

        <b-alert
            v-else-if="$hasPermission('can_have_journal')"
            show
        >
            <b>Warning:</b> You cannot update this journal until
            {{ assignment.is_group_assignment ? 'all group members' : 'you' }}
            visit the assignment though the LMS (Canvas) course
            '{{ assignment.active_lti_course.name }}' at least once.
        </b-alert>
    </div>
</template>

<script>
export default {
    props: {
        assignment: {
            type: Object,
            required: true,
        },
        journal: {
            type: Object,
            required: true,
        },
    },
}
</script>
