<template>
    <wide-content>
        <bread-crumb/>
        <b-card class="no-hover">
            <b-alert
                v-if="isChanged"
                show
            >
                <b>Note</b>: changes are not saved.
            </b-alert>
            <b-table-simple
                striped
                responsive
                class="role-config-table"
            >
                <b-thead>
                    <b-tr>
                        <b-th/>
                        <b-th
                            v-for="role in roles"
                            :key="`th-${role}`"
                        >
                            {{ role }}
                            <icon
                                v-if="!undeleteableRoles.includes(role)"
                                name="trash"
                                class="trash-icon"
                                @click.native="deleteRole(role)"
                            />
                        </b-th>
                        <b-th>
                            <span
                                class="darken-on-hover text-grey cursor-pointer unselectable"
                                @click="modalShow = !modalShow"
                            >
                                <icon
                                    name="plus"
                                    class="shift-up-3"
                                />
                                Add Role
                            </span>
                        </b-th>
                    </b-tr>
                </b-thead>
                <b-tbody>
                    <b-tr
                        v-for="permission in permissions"
                        :key="permission"
                    >
                        <b-td class="permission-column">
                            <b>{{ formatPermissionString(permission) }}</b>
                        </b-td>
                        <b-td
                            v-for="role in roles"
                            :key="`${role}-${permission}`"
                        >
                            <b-form-checkbox
                                v-model="roleConfig[getIndex(role)][permission]"
                                :class="{ 'input-disabled': essentialPermission(role, permission) }"
                                inline
                            />
                        </b-td>
                        <b-td>
                            <b-form-checkbox
                                class="input-disabled"
                            />
                        </b-td>
                    </b-tr>
                </b-tbody>
            </b-table-simple>
        </b-card>

        <transition name="fade">
            <b-button
                v-if="isChanged"
                class="green-button fab"
                @click="update()"
            >
                <icon
                    name="save"
                    scale="1.5"
                />
            </b-button>
        </transition>

        <b-modal
            v-model="modalShow"
            title="New Role"
            size="lg"
            hideFooter
            noEnforceFocus
            @shown="focusRoleNameInput"
        >
            <b-card class="no-hover">
                <b-form-input
                    ref="roleNameInput"
                    v-model="newRole"
                    class="multi-form theme-input"
                    required
                    placeholder="Role name"
                    @keyup.enter.native="addRole"
                />
                <b-button
                    class="red-button float-left"
                    @click="modalShow = false"
                >
                    <icon name="ban"/>
                    Cancel
                </b-button>
                <b-button
                    class="green-button float-right"
                    @click="addRole"
                >
                    <icon name="user-plus"/>
                    Create new role
                </b-button>
            </b-card>
        </b-modal>
    </wide-content>
</template>

<script>
import BreadCrumb from '@/components/assets/BreadCrumb.vue'
import WideContent from '@/components/columns/WideContent.vue'

import commonAPI from '@/api/common.js'
import roleAPI from '@/api/role.js'

export default {
    name: 'UserRoleConfiguration',
    components: {
        WideContent,
        BreadCrumb,
    },
    props: {
        cID: {
            required: true,
        },
    },
    data () {
        return {
            roles: [],
            permissions: [],
            roleConfig: [],
            originalRoleConfig: [],
            defaultRoles: [],
            undeleteableRoles: ['Student', 'TA', 'Teacher'],
            modalShow: false,
            newRole: '',
            essentialPermissions: { Teacher: ['can_edit_course_roles', 'can_edit_course_details'] },
            setRoleConfig: false,
            isChanged: false,
        }
    },
    watch: {
        roleConfig: {
            handler () {
                if (this.setRoleConfig) {
                    this.isChanged = true
                }
            },
            deep: true,
        },
    },
    created () {
        /* Initialises roles, permissions and role config as well as their defaults.
         * Roles and Permissions objects need to exist as deepcopy depends on then. */
        roleAPI.getFromCourse(this.cID)
            .then((roleConfig) => {
                this.roleConfig = roleConfig

                roleConfig.forEach((role) => {
                    this.defaultRoles.push(role.name)
                    this.roles.push(role.name)
                })
                this.permissions = Object.keys(roleConfig[0])
                this.permissions.splice(this.permissions.indexOf('id'), 1)
                this.permissions.splice(this.permissions.indexOf('name'), 1)
                this.permissions.splice(this.permissions.indexOf('course'), 1)

                this.originalRoleConfig = this.deepCopyRoles(roleConfig)

                this.$nextTick(() => { this.setRoleConfig = true })
            })
    },
    methods: {
        essentialPermission (role, permission) {
            return this.essentialPermissions[role] && this.essentialPermissions[role].includes(permission)
        },
        getIndex (role) {
            return this.roleConfig.findIndex((p) => p.name === role)
        },
        callocRoleObject (role) {
            /* Initialises a role object with the given name, the pages cID
             * and permissions object with all  corresponding permissions set to false. */
            const newPermissions = {}

            for (let i = 0; i < this.permissions.length; i++) {
                newPermissions[this.permissions[i]] = 0
            }

            return { name: role, cID: this.cID, permissions: newPermissions }
        },
        deepCopyRoles (roles) {
            const deepCopy = []

            for (let i = 0; i < roles.length; i++) {
                deepCopy.push({})
                Object.keys(roles[i]).forEach((key) => {
                    deepCopy[i][key] = roles[i][key]
                })
            }

            return deepCopy
        },
        addRole () {
            /* Adds a new role, clearing the input buffer and updating the
             * roles list and roleconfiguration objects. */
            this.roleConfig.push(this.callocRoleObject(this.newRole))
            this.roles.push(this.newRole)

            this.modalShow = false
            this.newRole = ''
        },
        focusRoleNameInput () {
            /* Ensures the modal name field is focused upon the modal opening. */
            this.$refs.roleNameInput.focus()
        },
        update () {
            roleAPI.update(this.cID, this.roleConfig, { customSuccessToast: 'Course roles successfully updated.' })
                .then(() => {
                    this.originalRoleConfig = this.deepCopyRoles(this.roleConfig)
                    this.defaultRoles = Array.from(this.roles)
                    this.checkPermission()
                    this.$nextTick(() => { this.isChanged = false })
                })
        },
        formatPermissionString (str) {
            /* Converts underscores to spaces and capatilises the first letter. */
            const temp = str.split('_').join(' ')
            return temp[0].toUpperCase() + temp.slice(1)
        },
        deleteRole (role) {
            if (window.confirm(`Are you sure you want to delete the role "${role}" from this course?`)) {
                if (this.defaultRoles.includes(role)) {
                    /* handle server update. */
                    roleAPI.delete(this.cID, role, { customSuccessToast: 'Role deleted successfully!' })
                        .then(() => {
                            this.deleteRoleLocalConfig(role)
                            this.deleteRoleServerLoadedConfig(role)
                        })
                } else {
                    this.deleteRoleLocalConfig(role)
                }
            }
        },
        deleteRoleLocalConfig (role) {
            let i = this.roleConfig.findIndex((p) => p.name === role)
            this.roleConfig.splice(i, 1)
            i = this.roles.findIndex((p) => p === role)
            this.roles.splice(i, 1)
        },
        deleteRoleServerLoadedConfig (role) {
            let i = this.originalRoleConfig.findIndex((p) => p.name === role)
            this.originalRoleConfig.splice(i, 1)
            i = this.defaultRoles.findIndex((p) => p === role)
            this.defaultRoles.splice(i, 1)
        },
        checkPermission () {
            commonAPI.getPermissions(this.cID)
                .then((coursePermissions) => {
                    this.$store.commit(
                        'user/UPDATE_PERMISSIONS',
                        { permissions: coursePermissions, key: `course${this.cID}` },
                    )
                    if (!this.$hasPermission('can_edit_course_roles')) { this.$router.push({ name: 'Home' }) }
                })
        },
        checkChanged () {
            for (let i = 0; i < this.roleConfig.length; i++) {
                for (let j = 0; j < this.permissions.length; j++) {
                    if (this.roleConfig[i][this.permissions[j]] !== this.originalRoleConfig[i][this.permissions[j]]) {
                        return true
                    }
                }
            }

            return false
        },
    },
    beforeRouteLeave (to, from, next) {
        if (this.checkChanged()
            && !window.confirm('Unsaved changes will be lost if you leave. Do you wish to continue?')) {
            next(false)
            return
        }

        next()
    },
}
</script>

<style lang="sass">
.role-config-table
    th
        text-align: center
    td
        text-align: center
        align-items: center
        .custom-checkbox
            margin: 0px
            padding-left: 2em
    .permission-column
        text-align: left !important
</style>
