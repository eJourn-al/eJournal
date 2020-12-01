<template>
    <content-columns>
        <bread-crumb
            slot="main-content-column"
            @edit-click="handleEdit()"
        />
        <load-wrapper
            slot="main-content-column"
            :loading="loadingJournals"
        >
            <div v-if="journals.length > 0">
                <journal-card
                    v-for="journal in journals"
                    :key="`join-journal-${journal.id}`"
                    :journal="journal"
                    :assignment="assignment"
                    :class="{
                        'input-disabled': (journal.author_limit != 0 && journal.author_count >= journal.author_limit)
                            || journal.locked,
                    }"
                    @click.native="joinJournal(journal.id)"
                />
            </div>
            <main-card
                v-else
                text="No journals for this assignment"
                class="no-hover"
            >
                Please ask your teacher to create a journal for you to join.
            </main-card>
        </load-wrapper>
    </content-columns>
</template>


<script>
import breadCrumb from '@/components/assets/BreadCrumb.vue'
import contentColumns from '@/components/columns/ContentColumns.vue'
import journalCard from '@/components/assignment/JournalCard.vue'
import loadWrapper from '@/components/loading/LoadWrapper.vue'
import mainCard from '@/components/assets/MainCard.vue'

import assignmentAPI from '@/api/assignment.js'
import journalAPI from '@/api/journal.js'

export default {
    name: 'JoinJournal',
    components: {
        contentColumns,
        breadCrumb,
        mainCard,
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
