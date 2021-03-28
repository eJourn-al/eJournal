import axios from 'axios'

axios.defaults.baseURL = CustomEnv.API_URL

const conn = axios.create()

// An instance without refresh interceptor
const connRefresh = axios.create()

const connDownFile = axios.create({
    responseType: 'arraybuffer',
    headers: {
        'Content-Type': 'multipart/form-data',
    },
})

const connSentry = axios.create({
    /* /api/0/projects/{organization_slug}/{project_slug}/ */
    baseURL: `${CustomEnv.SENTRY_URL}api/0/projects/${CustomEnv.SENTRY_ORG}/${CustomEnv.SENTRY_PROJECT}/`, // eslint-disable-line
    headers: {
        Authorization: `DSN ${CustomEnv.SENTRY_DSN}`,
    },
})

export default {
    conn,
    connRefresh,
    connDownFile,
    connSentry,
}
