<template>
    <b-card :class="color">
        <div class="float-right">
            <slot/>
        </div>
        <h2 class="theme-h2">
            {{ line1 }}
        </h2>
        <b-badge
            pill
            class="background-blue"
        >
            {{ line2 }}
        </b-badge>
    </b-card>
</template>

<script>
export default {
    props: ['line1', 'line2', 'color'],
}
</script>
