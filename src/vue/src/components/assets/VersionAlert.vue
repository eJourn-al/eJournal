<template>
    <b-alert
        :show="showVersionAlert"
        dismissible
        @dismissed="hideVersionAlert"
    >
        A new version of eJournal has been released: <b>{{ version }}</b>.
        Read the changelog
        <a
            href="https://www.ejournal.app/changelog.html"
            target="_blank"
        >
            <b>here</b>
        </a>.
    </b-alert>
</template>
<script>
export default {
    data () {
        return {
            version: CurrentRelease.version,
        }
    },
    computed: {
        showVersionAlert () {
            return this.$store.getters['preferences/saved'].hide_version_alert !== this.version
        },
    },
    methods: {
        hideVersionAlert () {
            this.$store.commit('preferences/CHANGE_PREFERENCES', { hide_version_alert: this.version })
        },
    },
}

</script>
