<!--
    Breadcrumb vue component
    Breadcrumb mirrors the current router link
    Caches named view names in store
    Settings object allows aliasing of page names and creation of new named routes
-->

<template>
    <div class="breadcrumb-container">
        <h4
            v-if="crumbs.length > 1"
            class="theme-h4"
        >
            <span>
                <b-link
                    v-for="crumb in crumbs.slice(0, -1)"
                    :key="crumb.route"
                    :to="{ name: crumb.routeName }"
                    class="crumb"
                >
                    {{ crumb.displayName }}
                </b-link>
                <b-link :to="{ name: crumbs[crumbs.length-2].routeName }">
                    <icon
                        name="level-up-alt"
                        class="shift-up-2 cursor-pointer"
                    />
                </b-link>
            </span>
        </h4>
        <h1
            v-if="crumbs.length > 0 && crumbs.slice(-1)[0].displayName"
            class="theme-h1"
        >
            <span class="title">
                {{ crumbs.slice(-1)[0].displayName }}
                <slot/>
            </span>
            <b-button
                v-if="canEdit()"
                class="orange-button edit-button"
                pill
                @click="editClick()"
            >
                <icon name="edit"/>
                Edit
            </b-button>
        </h1>
        <version-alert class="d-block"/>
    </div>
</template>

<script>
import store from '@/Store.vue'
import versionAlert from '@/components/assets/VersionAlert.vue'

import commonAPI from '@/api/common.js'

export default {
    components: {
        versionAlert,
    },
    /*
        aliases: aliases for unnamed vews
        namedViews: list of named views, with associated data field in get_names and primary parameter
    */
    data () {
        return {
            settings: {
                aliases: {
                    Home: 'Courses',
                    AssignmentEditor: 'Assignment Editor',
                    CourseEdit: 'Course Editor',
                    AdminPanel: 'Admin Panel',
                    AssignmentsOverview: 'Assignments',
                    UserRoleConfiguration: 'Permission Manager',
                    JoinJournal: 'Join a Journal',
                },
                namedViews: {
                    Course: { apiReturnValue: 'course', primaryParam: 'cID' },
                    Assignment: { apiReturnValue: 'assignment', primaryParam: 'aID' },
                    Journal: { apiReturnValue: 'journal', primaryParam: 'jID' },
                },
            },
            cachedMap: {},
            crumbs: [],
        }
    },
    created () {
        this.findRoutes()
        this.addDisplayNames()
        this.fillCache()
    },
    methods: {
        // Match routes that prepend the current path, create incomplete crumbs
        findRoutes () {
            const routeMatched = this.$route.matched[0].path
            const routerRoutes = this.$router.options.routes
            routerRoutes.sort((a, b) => a.path.length - b.path.length)
            // Add every matched (sub)route with params substituted to use as key
            routerRoutes.slice(1).forEach((route) => {
                if (routeMatched.startsWith(route.path)) {
                    let fullpath = route.path
                    Object.entries(this.$route.params).forEach((kvpair) => {
                        fullpath = fullpath.replace(`:${kvpair[0]}`, kvpair[1])
                    })
                    this.crumbs.push({ route: fullpath, routeName: route.name, displayName: null })
                }
            })
            // Remove the name of the journal author if the user can have a journal themself
            if (this.$route.name === 'Journal' && this.$hasPermission('can_have_journal')) {
                this.crumbs.pop()
            }
        },
        // Load the displayname map from cache, complete crumbs from cache where possible, do aliasing
        addDisplayNames () {
            this.cachedMap = store.state.cachedMap

            this.crumbs.forEach((crumb) => {
                if (!this.settings.namedViews[crumb.routeName]) {
                    crumb.displayName = this.settings.aliases[crumb.routeName] || crumb.routeName
                } else {
                    crumb.displayName = this.cachedMap[crumb.route] || null
                }
            })
        },
        // If any are still missing display names (not in cache), request the names and set them in cache
        fillCache () {
            const crumbsMissingDisplayName = this.crumbs.filter(crumb => !crumb.displayName)

            // Incrementally build request
            const request = {}
            crumbsMissingDisplayName.forEach((crumb) => {
                const paramName = this.settings.namedViews[crumb.routeName].primaryParam
                request[paramName] = this.$route.params[paramName]
            })

            if (crumbsMissingDisplayName.length > 0) {
                commonAPI.getNames(request)
                    .then((names) => {
                        crumbsMissingDisplayName.forEach((crumb) => {
                            crumb.displayName = names[this.settings.namedViews[crumb.routeName].apiReturnValue]
                            this.cachedMap[crumb.route] = crumb.displayName
                        })
                    })
                    .then(() => { store.setCachedMap(this.cachedMap) })
            }
        },
        editClick () {
            this.$emit('edit-click')
        },
        canEdit () {
            const pageName = this.$route.name

            if ((pageName === 'Course' && this.$hasPermission('can_edit_course_details'))
                || (pageName === 'Assignment' && this.$hasPermission('can_edit_assignment'))) {
                return true
            }

            return false
        },
    },
}
</script>

<style lang="sass">
.breadcrumb-container
    padding-right: 10px
    .crumb:after
        content: ' / '
    .alert
        margin-right: -10px
    .title
        margin-right: 10px
    .edit-button
        font-size: 0.7em !important
        vertical-align: middle
</style>
