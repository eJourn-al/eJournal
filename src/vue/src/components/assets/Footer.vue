<template>
    <footer class="small">
        &copy; {{ new Date().getFullYear() }} - eJournal
        <a
            href="https://www.eJournal.app/changelog"
            target="_blank"
            class="text-grey"
        >
            {{ version }}</a>
        -
        <a
            href="mailto:support@eJournal.app"
            target="_blank"
            class="text-grey"
        >
            support@eJournal.app</a>
        -
        <a
            href="https://www.eJournal.app/privacy-policy"
            target="_blank"
            class="text-grey"
        >
            Privacy policy
        </a>
    </footer>
</template>

<script>
export default {
    data () {
        return {
            version: CurrentRelease.version,
        }
    },
}

</script>

<style lang="sass">
footer
    color: grey
    text-align: center
    width: 100%
    margin: 10px 0px
    a
        text-decoration: underline !important
</style>
