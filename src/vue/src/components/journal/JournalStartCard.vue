<template>
    <b-card
        v-if="assignment !== null"
        class="no-hover"
        :class="$root.getBorderClass($route.params.cID)"
    >
        <b-row
            no-gutters
            class="multi-form"
        >
            <span class="theme-h2">{{ assignment.name }}</span>

            <slot name="edit-button"/>
        </b-row>


        <sandboxed-iframe
            v-if="assignment.description"
            :content="assignment.description"
        />
        <hr/>
        <span
            v-if="assignment.unlock_date && new Date(assignment.unlock_date) > new Date()"
            class="text-grey"
        >
            This assignment is locked and will be made available later<br/>
            Unlock date: {{ $root.beautifyDate(assignment.unlock_date) }}
        </span>
        <span
            v-else
            class="text-grey"
        >
            <span v-if="assignment.due_date">
                <span v-if="new Date() > new Date(assignment.due_date) && !assignment.lock_date">
                    The due date for this assignment has passed<br/>
                </span>
                Due date: {{ $root.beautifyDate(assignment.due_date) }}<br/>
            </span>
            <span v-if="assignment.lock_date">
                <span v-if="new Date(assignment.lock_date) < new Date()">
                    This assignment has been locked<br/>
                </span>
                Lock date: {{ $root.beautifyDate(assignment.lock_date) }}<br/>
            </span>
            <span v-if="assignment.points_possible">
                Points possible: {{ assignment.points_possible }}<br/>
            </span>
        </span>
    </b-card>
</template>

<script>
import sandboxedIframe from '@/components/assets/SandboxedIframe.vue'

export default {
    components: {
        sandboxedIframe,
    },
    props: ['assignment'],
}
</script>
