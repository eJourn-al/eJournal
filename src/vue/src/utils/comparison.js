import store from '@/store/index.js'

export default {
    date (a, b) {
        if (!a.deadline.date) { return 1 }
        if (!b.deadline.date) { return -1 }
        return new Date(a.deadline.date) - new Date(b.deadline.date)
    },

    markingNeededOwnGroups (a, b) {
        const markingNeededA = (
            a.stats.needs_marking_own_groups
            + a.stats.unpublished_own_groups
            + ((a.stats.import_requests_own_groups) ? a.stats.import_requests_own_groups : 0)
        )
        const markingNeededB = (
            b.stats.needs_marking_own_groups
            + b.stats.unpublished_own_groups
            + ((b.stats.import_requests_own_groups) ? b.stats.import_requests_own_groups : 0)
        )
        return markingNeededB - markingNeededA
    },

    markingNeededAll (a, b) {
        const markingNeededA = (
            a.stats.needs_marking
            + a.stats.unpublished
            + ((a.stats.import_requests) ? a.stats.import_requests : 0)
        )
        const markingNeededB = (
            b.stats.needs_marking
            + b.stats.unpublished
            + ((b.stats.import_requests) ? b.stats.import_requests : 0)
        )
        return markingNeededB - markingNeededA
    },

    nodeDueDateHasPassed (node, assignment) {
        const currentDate = new Date()
        const dueDate = new Date((node === store.getters['timeline/endNode']) ? assignment.due_date : node.due_date)

        return currentDate > dueDate
    },
    nodeLockDateHasPassed (node) {
        if (!node.lock_date) {
            return false
        }

        const currentDate = new Date()
        const lockDate = new Date(node.lock_date)

        return currentDate > lockDate
    },
}
