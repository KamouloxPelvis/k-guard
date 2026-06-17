<script setup>
/**
 * Main Entry Point Component.
 * The logic is handled within specific views and the router.
 */
</script>

<template>
  <router-view v-slot="{ Component }">
    <keep-alive>
      <component :is="Component" />
    </keep-alive>
  </router-view>
</template>

<style>
/* Global styles are managed via style.css to prevent scoped conflicts 
 * and maintain consistent branding across the SPA.
 */
</style>