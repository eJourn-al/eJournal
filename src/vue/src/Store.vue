<script>
export default {
    debug: false,
    state: {
        cachedMap: {},
        filteredJournals: [],
    },
    setCachedMap (cachedMap) {
        this.state.cachedMap = cachedMap
    },
    setFilteredJournals (journals, order = true, groups = null, searchValue = null, sortBy = 'name') {
        function compare (a, b) {
            if (a < b) { return order ? 1 : -1 }
            if (a > b) { return order ? -1 : 1 }
            return 0
        }

        const sortOptions = {
            name: (a, b) => compare(a.name, b.name),
            username: (a, b) => {
                if (a.author_count > 0 && b.author_count > 0) {
                    return compare(a.usernames, b.usernames)
                } else if (a.author_count > 0) {
                    return -1
                } else if (b.author_count > 0) {
                    return 1
                }
                return 0
            },
            markingNeeded: (a, b) => compare(a.needs_marking, b.needs_marking),
            points: (a, b) => compare(a.grade, b.grade),
            importRequests: (a, b) => compare(a.import_requests, b.import_requests),
        }

        function groupFilter (journal) {
            if (groups === null) {
                return false
            }

            return groups.some(group => journal.groups.includes(group.id))
        }

        function searchFilter (journal) {
            return journal.name.toLowerCase().includes(searchValue.toLowerCase())
                || journal.usernames.toLowerCase().includes(searchValue.toLowerCase())
                || journal.full_names.toLowerCase().includes(searchValue.toLowerCase())
        }
        let filteredJournals = journals
        if (groups !== null && groups.length !== 0) {
            filteredJournals = filteredJournals.filter(groupFilter)
        }
        if (searchValue !== null && searchValue !== '') {
            filteredJournals = filteredJournals.filter(searchFilter)
        }
        filteredJournals.sort(sortOptions[sortBy])
        this.state.filteredJournals = filteredJournals
    },
    debugOn () {
        this.debug = true
    },
    debugOff () {
        this.debug = false
    },
    clearCache () {
        this.state.cachedMap = []
    },
}
</script>
