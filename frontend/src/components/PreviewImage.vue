<template>
  <div style="display:inline-block;cursor:pointer" @click="open=true">
    <img :src="src" style="width:56px;height:56px;object-fit:cover;border-radius:4px" />
    <el-dialog v-model="open" :show-header="false" width="fit-content" :close-on-click-modal="true" append-to-body center>
      <img :src="src" style="max-width:90vw;max-height:85vh;display:block" />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
defineProps<{ src: string }>()
const open = ref(false)
</script>

<style>
.el-dialog .el-dialog__body:has(> img) { padding: 0; line-height: 0; }
</style>
