<!--
    Component that will show all the comments of a given entry and support
    the possibility to add comments when the right permissions are met.
-->
<template>
    <div>
        <div v-if="comments">
            <comment-card
                v-for="comment in comments"
                :key="`comment-${eID}-${comment.id}`"
                :passedComment="comment"
                @deleteComment="deleteComment"
            />
        </div>
        <comment-card
            v-if="$hasPermission('can_comment')"
            :createCard="true"
            :passedComment="createComment"
            :eID="eID"
            @deleteComment="deleteComment"
            @change-option="changeButtonOption"
            @new-comment="addComment"
            @publish-grade="(e) => $emit('publish-grade', e)"
        />
    </div>
</template>

<script>
import commentCard from '@/components/entry/CommentCard.vue'

import commentAPI from '@/api/comment.js'

export default {
    components: {
        commentCard,
    },
    props: {
        eID: {
            required: true,
        },
        entryGradePublished: {
            type: Boolean,
            default: false,
        },
    },
    data () {
        return {
            comments: null,
            saveRequestInFlight: false,
            createComment: {
                id: 0,
                text: '',
                files: [],
                author: {
                    profile_picture: this.$store.getters['user/profilePicture'],
                    full_name: this.$store.getters['user/fullName'],
                },
            },
        }
    },
    watch: {
        eID () {
            this.tempComment = ''
            this.getComments()
        },
        entryGradePublished () {
            this.getComments()
        },
    },
    created () {
        this.getComments()
    },
    methods: {
        addComment (comment) {
            this.comments.push(comment)
        },
        getComments () {
            commentAPI.getFromEntry(this.eID)
                .then((comments) => { this.comments = comments })
        },
        changeButtonOption (option) {
            this.$store.commit('preferences/CHANGE_PREFERENCES', { comment_button_setting: option })
        },
        deleteComment (cID) {
            if (window.confirm('Are you sure you want to delete this comment?')) {
                commentAPI.delete(cID, { responseSuccessToast: true })
                    .then(() => {
                        // Remove comment from the list of comments
                        this.comments.splice(this.comments.map(c => c.id).indexOf(cID), 1)
                    })
            }
        },
    },
}
</script>
