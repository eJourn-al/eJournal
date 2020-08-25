<template>
    <journal-non-student
        v-if="$hasPermission('can_grade')"
        ref="journal-non-student-ref"
        :cID="cID"
        :aID="aID"
        :jID="jID"
    />
    <journal-student
        v-else-if="$hasPermission('can_have_journal')"
        ref="journal-student-ref"
        :cID="cID"
        :aID="aID"
        :jID="jID"
    />
</template>

<script>
import journalStudent from '@/components/journal/JournalStudent.vue'
import journalNonStudent from '@/components/journal/JournalNonStudent.vue'

export default {
    name: 'Journal',
    components: {
        journalStudent,
        journalNonStudent,
    },
    props: ['cID', 'aID', 'jID'],
    beforeRouteLeave (to, from, next) {
        if (this.$hasPermission('can_have_journal') && !this.$refs['journal-student-ref'].safeToLeave()) {
            next(false)
            return
        }

        if (this.$hasPermission('can_grade') && !this.$refs['journal-non-student-ref'].safeToLeave()) {
            next(false)
            return
        }

        next()
    },
}
</script>

<style lang="sass">
@import '~sass/partials/timeline-page-layout.sass'
</style>
