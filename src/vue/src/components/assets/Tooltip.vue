<template>
    <icon
        v-b-tooltip:hover="title"
        name="info-circle"
        class="fill-grey help-cursor shift-up-3"
        tabindex="-1"
    />
</template>
<script>

export default {
    props: ['tip'],
    computed: {
        title () {
            return this.tip.replace(/\s+/g, ' ')
        },
    },
}

</script>
