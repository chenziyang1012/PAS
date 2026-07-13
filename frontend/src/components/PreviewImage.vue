<template>
  <div style="display:inline-block;cursor:pointer" @click="openPreview">
    <img :src="src" style="width:56px;height:56px;object-fit:cover;border-radius:4px" />
    <Teleport to="body">
      <div v-if="open" class="lightbox-overlay" @click.self="closePreview" @wheel.prevent="onWheel">
        <img :src="src" class="lightbox-img" :style="{transform:`scale(${scale})`}" draggable="false" @click.stop />
        <div class="lightbox-close" @click="closePreview">✕</div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
defineProps<{ src: string }>()
const open = ref(false)
const scale = ref(1)

function openPreview() {
  scale.value = 1
  open.value = true
}

function closePreview() {
  open.value = false
  scale.value = 1
}

function onWheel(e: WheelEvent) {
  scale.value = Math.min(10, Math.max(0.2, scale.value - e.deltaY * 0.002))
}
</script>

<style>
.lightbox-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  z-index: 9999;
  background: rgba(0,0,0,0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: zoom-out;
  user-select: none;
}
.lightbox-img {
  max-width: 95vw;
  max-height: 95vh;
  transition: transform 0.1s;
  transform-origin: center;
  cursor: default;
}
.lightbox-close {
  position: absolute;
  top: 20px;
  right: 28px;
  color: #fff;
  font-size: 28px;
  cursor: pointer;
  z-index: 10000;
  opacity: 0.7;
  transition: opacity 0.2s;
}
.lightbox-close:hover { opacity: 1; }
</style>
