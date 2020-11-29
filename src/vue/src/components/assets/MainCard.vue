<template>
    <b-card>
        <h2 class="theme-h2">
            {{ text }}
        </h2>
        <slot/>
    </b-card>
</template>

<script>
export default {
    props: ['text'],
}
</script>
