<template>
    <icon
        v-intro="'That\'s it! If you have any more questions, do not hesitate to contact us via the \
        support button at the bottom of any page. This tutorial can be consulted again by clicking \
        the info sign.'"
        v-intro-step="5"
        v-b-tooltip:hover="'Click to start a tutorial for this page'"
        name="info-circle"
        scale="1.75"
        class="info-icon shift-up-5 ml-1"
    />
</template>

<script>
export default {
    name: 'FormatTutorialIcon',
}
</script>
