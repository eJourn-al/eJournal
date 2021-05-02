<template>
    <div class="p-4 text-center background-light-grey round-border">
        <h2 class="theme-h2">
            No {{ subject }} found
        </h2>
        {{ explanation }}
        <slot/>
    </div>
</template>

<script>
export default {
    props: {
        subject: {
            required: true,
        },
        explanation: {
            required: true,
        },
    },
}
</script>
