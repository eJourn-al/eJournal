<template>
    <content-single-column>
        <bread-crumb/>
        <load-wrapper
            :loading="loadingJournals"
        >
            <template v-if="journals.length > 0">
                <journal-card
                    v-for="journal in journals"
                    :key="`join-journal-${journal.id}`"
                    :isLink="false"
                    :journal="journal"
                    :assignment="assignment"
                    :class="{
                        'input-disabled': (journal.author_limit != 0 && journal.author_count >= journal.author_limit)
                            || journal.locked,
                    }"
                >
                    <b-button
                        class="green-button float-right"
                        variant="link"
                        @click="joinJournal(journal.id)"
                    >
                        <icon name="user-plus"/>
                        Join
                    </b-button>
                </journal-card>
            </template>
            <not-found
                v-else
                subject="journals"
                explanation="Please ask your teacher to create a journal for you to join."
            />
        </load-wrapper>
    </content-single-column>
</template>

<script>
import breadCrumb from '@/components/assets/BreadCrumb.vue'
import contentSingleColumn from '@/components/columns/ContentSingleColumn.vue'
import journalCard from '@/components/assignment/JournalCard.vue'
import loadWrapper from '@/components/loading/LoadWrapper.vue'

import assignmentAPI from '@/api/assignment.js'
import journalAPI from '@/api/journal.js'

export default {
    name: 'JoinJournal',
    components: {
        contentSingleColumn,
        breadCrumb,
        journalCard,
        loadWrapper,
    },
    props: {
        cID: {
            required: true,
        },
        aID: {
            required: true,
        },
    },
    data () {
        return {
            journals: [],
            assignment: null,
            loadingJournals: true,
        }
    },
    created () {
        const initialCalls = []
        initialCalls.push(assignmentAPI.get(this.aID, this.cID))
        initialCalls.push(journalAPI.list(this.cID, this.aID))
        Promise.all(initialCalls).then((results) => {
            this.loadingJournals = false
            this.assignment = results[0]
            this.journals = results[1]
        })
    },
    methods: {
        joinJournal (jID) {
            journalAPI.join(jID)
                .then((journal) => {
                    this.$router.push({
                        name: 'Journal',
                        params: {
                            cID: this.cID, aID: this.aID, jID: journal.id,
                        },
                    })
                })
        },
    },
}
</script>
