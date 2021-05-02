<template>
    <b-card>
        <template slot="header">
            <slot
                name="edit-button"
            />
            <h2 class="theme-h2">
                {{ currentNode.display_name }}
            </h2>
            <span class="small">
                Goal: <b>{{ currentNode.target }}</b> point<span v-if="currentNode.target > 1">s</span>
                (<b>{{ score > currentNode.target ? currentNode.target : score }}</b> achieved)<br/>
            </span>
        </template>
        <sandboxed-iframe
            v-if="currentNode.description"
            :content="currentNode.description"
        />
        <files-list
            v-if="currentNode.attached_files && currentNode.attached_files.length > 0"
            :files="currentNode.attached_files"
            class="mt-2 mr-2 align-top"
        />
        <deadline-date-display
            :subject="currentNode"
            class="mt-2 align-top"
        /><br/>
    </b-card>
</template>

<script>
import DeadlineDateDisplay from '@/components/assets/DeadlineDateDisplay.vue'
import filesList from '@/components/assets/file_handling/FilesList.vue'
import sandboxedIframe from '@/components/assets/SandboxedIframe.vue'

export default {
    components: {
        sandboxedIframe,
        filesList,
        DeadlineDateDisplay,
    },
    props: ['nodes', 'currentNode', 'bonusPoints'],
    computed: {
        score () {
            /* The function will update a given progressNode by
            * going through all the nodes and count the published grades
            * so far. */
            let tempProgress = this.bonusPoints

            this.nodes.some((node) => {
                if (node.id === this.currentNode.id) { return true }

                if (node.type === 'e' || node.type === 'd') {
                    if (node.entry && node.entry.grade && node.entry.grade.published
                        && node.entry.grade.grade !== '0') {
                        tempProgress += parseFloat(node.entry.grade.grade)
                    }
                }

                return false
            })

            return tempProgress
        },
        accomplished () {
            return this.score >= this.currentNode.target
        },
        left () {
            return this.currentNode.target - this.score
        },
        scoreClass () {
            return {
                'text-green': this.accomplished,
                'text-red': !this.accomplished && new Date() > new Date(this.currentNode.due_date),
                'text-orange': !this.accomplished && new Date() < new Date(this.currentNode.due_date),
            }
        },
    },
}
</script>
