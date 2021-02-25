import auth from '@/api/auth.js'

export default {
    /* Return te needed variables for course/assignment create, connect and select
     */
    getLtiParams (jwtParams, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.post('get_lti_params_from_jwt', { jwt_params: jwtParams }, connArgs)
            .then((response) => response.data.params)
    },

    updateLtiGroups (jwtParams, connArgs = auth.DEFAULT_CONN_ARGS) {
        return auth.post('update_lti_groups', { jwt_params: jwtParams }, connArgs)
            .then((response) => response.data.params)
    },
}
