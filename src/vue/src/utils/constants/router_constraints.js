const PERMISSIONLESS_CONTENT = new Set([
    'Login',
    'LtiLogin',
    'LtiLaunch',
    'Register',
    'ErrorPage',
    'SetPassword',
    'EmailVerification',
    'Guest',
])

const UNAVAILABLE_WHEN_LOGGED_IN = new Set([
    'Login',
    'Guest',
    'Register',
])

export default {
    PERMISSIONLESS_CONTENT,
    UNAVAILABLE_WHEN_LOGGED_IN,
}
